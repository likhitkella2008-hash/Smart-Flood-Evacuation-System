"""
Turso LibSQL Cloud SQLite Adapter
==================================
Provides a synchronous, SQLite3-compatible interface for Turso LibSQL databases
using standard HTTP requests. Enables persistent database operations on serverless
platforms (e.g., Vercel, AWS Lambda) without native C-extension dependencies.
"""

import base64
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import requests

logger = logging.getLogger("SmartFloodTurso")


def serialize_arg(val: Any) -> Dict[str, Any]:
    """Serializes a Python value into Turso v2 pipeline JSON parameter format."""
    if val is None:
        return {"type": "null"}
    elif isinstance(val, bool):
        return {"type": "integer", "value": "1" if val else "0"}
    elif isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    elif isinstance(val, float):
        return {"type": "float", "value": val}
    elif isinstance(val, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(val).decode("ascii")}
    else:
        return {"type": "text", "value": str(val)}


def deserialize_val(val_obj: Any) -> Any:
    """Deserializes a Turso v2 pipeline JSON value into a Python primitive."""
    if not isinstance(val_obj, dict):
        return val_obj
    t = val_obj.get("type")
    if t == "null":
        return None
    elif t == "integer":
        raw = val_obj.get("value", 0)
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0
    elif t == "float":
        raw = val_obj.get("value", 0.0)
        try:
            return float(raw)
        except (ValueError, TypeError):
            return 0.0
    elif t == "text":
        return str(val_obj.get("value", ""))
    elif t == "blob":
        b64 = val_obj.get("base64", "")
        try:
            return base64.b64decode(b64)
        except Exception:
            return b""
    return val_obj.get("value")


class TursoRow:
    """
    Drop-in replacement for sqlite3.Row.
    Supports index-based access, column name access, and dict(row) conversion.
    """
    def __init__(self, cols: Sequence[str], values: Sequence[Any]):
        self._cols = list(cols)
        self._vals = list(values)
        self._map = dict(zip(self._cols, self._vals))

    def __getitem__(self, key: Union[int, str]) -> Any:
        if isinstance(key, int):
            return self._vals[key]
        return self._map[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def keys(self) -> List[str]:
        return list(self._cols)

    def values(self) -> List[Any]:
        return list(self._vals)

    def items(self):
        return self._map.items()

    def __iter__(self):
        # Allows dict(row) to unpack keys as in sqlite3.Row
        return iter(self._cols)

    def __len__(self) -> int:
        return len(self._cols)

    def __contains__(self, key: str) -> bool:
        return key in self._map

    def __repr__(self) -> str:
        return f"<TursoRow {self._map}>"


class TursoCursor:
    """Cursor implementation over Turso HTTP API."""
    def __init__(self, connection: "TursoConnection"):
        self.connection = connection
        self.description: Optional[Tuple[Any, ...]] = None
        self.lastrowid: Optional[int] = None
        self.rowcount: int = -1
        self._rows: List[TursoRow] = []
        self._index: int = 0

    def execute(self, sql: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> "TursoCursor":
        clean_sql = sql.strip()
        args: List[Dict[str, Any]] = []

        if params is not None:
            if isinstance(params, (list, tuple)):
                args = [serialize_arg(p) for p in params]
            elif isinstance(params, dict):
                # Named parameters :param or @param
                pass

        req_payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": clean_sql,
                        "args": args
                    }
                },
                {"type": "close"}
            ]
        }

        resp_data = self.connection._post_pipeline(req_payload)
        self._parse_response(resp_data)
        return self

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> "TursoCursor":
        requests_list = []
        for params in seq_of_params:
            args = [serialize_arg(p) for p in params]
            requests_list.append({
                "type": "execute",
                "stmt": {
                    "sql": sql.strip(),
                    "args": args
                }
            })
        requests_list.append({"type": "close"})

        resp_data = self.connection._post_pipeline({"requests": requests_list})
        self._parse_response(resp_data)
        return self

    def _parse_response(self, data: Dict[str, Any]):
        results = data.get("results", [])
        if not results:
            self._rows = []
            self.description = None
            return

        # Check for errors in first statement
        first = results[0]
        if first.get("type") == "error":
            err_msg = first.get("error", {}).get("message", "Unknown Turso execution error")
            raise RuntimeError(f"Turso SQL Error: {err_msg}")

        resp = first.get("response", {})
        result = resp.get("result", {})

        raw_cols = result.get("cols", [])
        col_names = [c.get("name", f"col_{i}") for i, c in enumerate(raw_cols)]

        if col_names:
            self.description = tuple((name, None, None, None, None, None, None) for name in col_names)
        else:
            self.description = None

        self.rowcount = result.get("affected_row_count", 0)

        raw_last_id = result.get("last_insert_rowid")
        if raw_last_id is not None:
            try:
                self.lastrowid = int(raw_last_id)
            except (ValueError, TypeError):
                self.lastrowid = None
        else:
            self.lastrowid = None

        raw_rows = result.get("rows", [])
        parsed_rows = []
        for r in raw_rows:
            parsed_vals = [deserialize_val(v) for v in r]
            parsed_rows.append(TursoRow(col_names, parsed_vals))

        self._rows = parsed_rows
        self._index = 0

    def fetchone(self) -> Optional[TursoRow]:
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self) -> List[TursoRow]:
        remaining = self._rows[self._index:]
        self._index = len(self._rows)
        return remaining

    def fetchmany(self, size: int = 1) -> List[TursoRow]:
        end = min(self._index + size, len(self._rows))
        slice_rows = self._rows[self._index:end]
        self._index = end
        return slice_rows

    def close(self):
        self._rows = []
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self) -> TursoRow:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class TursoConnection:
    """Connection abstraction over Turso LibSQL HTTP endpoint."""
    def __init__(self, database_url: str, auth_token: Optional[str] = None):
        # Normalize protocol: libsql:// -> https://
        clean_url = database_url.strip()
        if clean_url.startswith("libsql://"):
            clean_url = "https://" + clean_url[len("libsql://"):]
        elif not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        # Remove trailing slash
        clean_url = clean_url.rstrip("/")
        if not clean_url.endswith("/v2/pipeline"):
            clean_url = f"{clean_url}/v2/pipeline"

        self.endpoint = clean_url
        self.auth_token = auth_token
        self.row_factory = TursoRow
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "SmartFloodRescue-TursoClient/1.0"
        })
        if self.auth_token:
            self._session.headers.update({
                "Authorization": f"Bearer {self.auth_token.strip()}"
            })

    def _post_pipeline(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._session.post(self.endpoint, json=payload, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Turso HTTP request failed (status {resp.status_code}): {resp.text}")
        return resp.json()

    def cursor(self) -> TursoCursor:
        return TursoCursor(self)

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> TursoCursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        # In HTTP pipeline mode, statements are automatically committed.
        pass

    def rollback(self):
        pass

    def close(self):
        self._session.close()


def connect(database_url: str, auth_token: Optional[str] = None) -> TursoConnection:
    """Creates a Turso LibSQL connection."""
    return TursoConnection(database_url, auth_token)
