"""
Smart Flood Evacuation & Rescue System - Emergency Prioritization Engine
========================================================================

Transparent, rule-based triage heuristic designed to assist emergency
dispatchers in organizing and prioritizing rescue requests.

Formula Breakdown (Max Theoretical Raw Score: 100):
---------------------------------------------------
1. Flood Level Score (0 - 35 points):
   - Level 1 (Low): 5 pts
   - Level 2 (Rising): 12 pts
   - Level 3 (Moderate): 20 pts
   - Level 4 (High): 28 pts
   - Level 5 (Critical): 35 pts

2. Occupants / Affected People Score (0 - 25 points):
   - 1 person: 4 pts
   - 2 - 4 people: 10 pts
   - 5 - 9 people: 18 pts
   - 10+ people: 25 pts

3. Vulnerable Population & Medical Need (0 - 25 points):
   - Urgent Medical Need: +20 pts (and immediately elevates triage status)
   - Elderly individuals (>=60y): +3 pts each (max 9 pts)
   - Children (<=12y): +3 pts each (max 9 pts)
   - Persons with disabilities / mobility needs: +5 pts each (max 12 pts)
   (Capped at 25 pts total for this category)

4. Elapsed Wait-Time Escalation (0 - 15 points):
   - < 30 minutes: 0 pts
   - 30 to 60 minutes: 4 pts
   - 1 to 2 hours: 8 pts
   - 2 to 4 hours: 12 pts
   - > 4 hours: 15 pts

Priority Thresholds:
--------------------
- CRITICAL: Score >= 70 OR Urgent Medical Flag == True OR (Flood Level == 5 AND People >= 5)
- HIGH:     Score >= 45
- MEDIUM:   Score >= 25
- LOW:      Score < 25

Note: This scoring system is a heuristic prioritization aid for triage
organization and should never be used to deny emergency assistance.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


def calculate_priority(
    flood_level: int,
    people: int,
    medical_urgent: bool = False,
    elderly_count: int = 0,
    children_count: int = 0,
    disability_count: int = 0,
    created_at: Optional[str] = None
) -> Tuple[float, str, List[str]]:
    """
    Computes priority score, category, and transparent contributing factors.

    Returns:
        (priority_score, priority_category, reasons_list)
    """
    reasons: List[str] = []
    score: float = 0.0

    # 1. Flood level scoring (0 - 35 pts)
    fl = max(1, min(5, int(flood_level or 1)))
    fl_points = {1: 5.0, 2: 12.0, 3: 20.0, 4: 28.0, 5: 35.0}
    pts_fl = fl_points.get(fl, 5.0)
    score += pts_fl
    reasons.append(f"Flood severity Level {fl}/5 (+{pts_fl:.0f} pts)")

    # 2. People affected scoring (0 - 25 pts)
    ppl = max(1, int(people or 1))
    if ppl >= 10:
        pts_ppl = 25.0
        reasons.append(f"Large group of {ppl} people (+25 pts)")
    elif ppl >= 5:
        pts_ppl = 18.0
        reasons.append(f"Family/group of {ppl} people (+18 pts)")
    elif ppl >= 2:
        pts_ppl = 10.0
        reasons.append(f"{ppl} people affected (+10 pts)")
    else:
        pts_ppl = 4.0
        reasons.append(f"Single individual affected (+4 pts)")
    score += pts_ppl

    # 3. Vulnerability scoring (0 - 25 pts)
    vuln_pts = 0.0
    is_medical = bool(medical_urgent)
    if is_medical:
        vuln_pts += 20.0
        reasons.append("URGENT: Critical medical assistance required (+20 pts)")

    eld = max(0, int(elderly_count or 0))
    if eld > 0:
        pts_eld = min(eld * 3.0, 9.0)
        vuln_pts += pts_eld
        reasons.append(f"{eld} elderly resident(s) requiring assistance (+{pts_eld:.0f} pts)")

    chld = max(0, int(children_count or 0))
    if chld > 0:
        pts_chld = min(chld * 3.0, 9.0)
        vuln_pts += pts_chld
        reasons.append(f"{chld} child/infant(s) requiring evacuation (+{pts_chld:.0f} pts)")

    dis = max(0, int(disability_count or 0))
    if dis > 0:
        pts_dis = min(dis * 5.0, 12.0)
        vuln_pts += pts_dis
        reasons.append(f"{dis} person(s) with mobility/disability needs (+{pts_dis:.0f} pts)")

    vuln_capped = min(vuln_pts, 25.0)
    score += vuln_capped

    # 4. Wait time escalation (0 - 15 pts)
    wait_pts = 0.0
    if created_at:
        try:
            # Parse created_at format "%Y-%m-%d %H:%M:%S"
            t_created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            minutes_waiting = (datetime.now() - t_created).total_seconds() / 60.0
            if minutes_waiting > 240:
                wait_pts = 15.0
                reasons.append(f"Critical wait duration: {minutes_waiting/60.0:.1f} hrs elapsed (+15 pts)")
            elif minutes_waiting > 120:
                wait_pts = 12.0
                reasons.append(f"Extended wait duration: {minutes_waiting/60.0:.1f} hrs elapsed (+12 pts)")
            elif minutes_waiting > 60:
                wait_pts = 8.0
                reasons.append(f"Wait duration: {minutes_waiting/60.0:.1f} hrs elapsed (+8 pts)")
            elif minutes_waiting > 30:
                wait_pts = 4.0
                reasons.append(f"Wait duration: {int(minutes_waiting)} mins elapsed (+4 pts)")
        except Exception:
            pass
    score += wait_pts

    # Normalize total score between 0 and 100
    final_score = min(100.0, max(0.0, round(score, 1)))

    # Determine priority category
    # Special escalation rule: urgent medical emergency or severe combination guarantees Critical
    if is_medical or (fl >= 5 and ppl >= 5) or final_score >= 70.0:
        category = "Critical"
    elif final_score >= 45.0:
        category = "High"
    elif final_score >= 25.0:
        category = "Medium"
    else:
        category = "Low"

    return final_score, category, reasons
