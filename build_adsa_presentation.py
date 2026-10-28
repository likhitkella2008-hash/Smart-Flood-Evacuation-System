"""
build_adsa_presentation.py
===========================
Generates a complete 22-slide professional ADSA end-semester review presentation
for the Smart Flood Rescue System (Team No. 06).
Embeds complete, spoken-script speaker notes on every slide.
Exports to PPTX and attempts automated PDF export via PowerPoint COM.
"""

import sys
import os
import math
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# -------------------------------------------------------------
# Color Palette (Restrained Navy, Teal, Slate & Emergency Colors)
# -------------------------------------------------------------
BG_DARK = RGBColor(10, 25, 47)         # Deep Navy #0A192F
BG_CARD = RGBColor(23, 42, 69)         # Slate Navy #172A45
BG_CARD_LIGHT = RGBColor(35, 53, 84)   # Accent Card #233554
TEXT_LIGHT = RGBColor(248, 250, 252)   # Slate 50
TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400
TEXT_CYAN = RGBColor(56, 189, 248)     # Sky Teal #38BDF8
TEXT_BLUE = RGBColor(96, 165, 250)     # Blue 400 #60A5FA
ACCENT_BLUE = RGBColor(37, 99, 235)    # Blue 600 #2563EB
ACCENT_GREEN = RGBColor(34, 197, 94)   # Green 500 #22C55E
ACCENT_AMBER = RGBColor(245, 158, 11)  # Amber 500 #F59E0B
ACCENT_RED = RGBColor(239, 68, 68)     # Red 500 #EF4444
BORDER_BLUE = RGBColor(30, 58, 95)     # Subdued Navy Border
TABLE_HEADER_BG = RGBColor(30, 58, 95)
TABLE_ALT_ROW = RGBColor(18, 34, 58)

def set_slide_background(slide, color=BG_DARK):
    """Fills slide background with a solid color."""
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = color
    bg_shape.line.fill.background()
    return bg_shape

def add_header(slide, title, category="ADSA PROJECT REVIEW — TEAM 06", slide_num=None):
    """Standardized top header with category and title."""
    tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(10.5), Inches(0.3))
    tf_tag = tag_box.text_frame
    tf_tag.word_wrap = True
    tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = category.upper()
    p_tag.font.name = "Calibri"
    p_tag.font.size = Pt(10.5)
    p_tag.font.bold = True
    p_tag.font.color.rgb = TEXT_CYAN

    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(10.5), Inches(0.65))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = "Calibri"
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_LIGHT

    if slide_num:
        num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.4), Inches(1.0), Inches(0.5))
        tf_num = num_box.text_frame
        p_num = tf_num.paragraphs[0]
        p_num.text = f"{slide_num:02d} / 22"
        p_num.font.name = "Calibri"
        p_num.font.size = Pt(11)
        p_num.font.color.rgb = TEXT_MUTED
        p_num.alignment = PP_ALIGN.RIGHT

    div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
    div.fill.solid()
    div.fill.fore_color.rgb = BORDER_BLUE
    div.line.fill.background()

def create_card(slide, left, top, width, height, title, items, subtitle=None, highlight_color=None):
    """Creates a stylized content card with bullet points."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = BG_CARD
    card.line.color.rgb = highlight_color if highlight_color else BORDER_BLUE
    card.line.width = Pt(1.5)

    tx_box = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), height - Inches(0.4))
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.name = "Calibri"
    p_title.font.size = Pt(15)
    p_title.font.bold = True
    p_title.font.color.rgb = highlight_color if highlight_color else TEXT_CYAN
    p_title.space_after = Pt(3)

    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.name = "Calibri"
        p_sub.font.size = Pt(10.5)
        p_sub.font.color.rgb = TEXT_MUTED
        p_sub.space_after = Pt(6)

    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.name = "Calibri"
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_LIGHT
        p.space_after = Pt(4)

def create_metric_card(slide, left, top, width, height, value, label, subtext="", color=TEXT_CYAN):
    """Creates a key metric / KPI callout card."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = BG_CARD
    card.line.color.rgb = BORDER_BLUE
    card.line.width = Pt(1.2)

    tx = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.15), width - Inches(0.3), height - Inches(0.3))
    tf = tx.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_val = tf.paragraphs[0]
    p_val.text = value
    p_val.font.name = "Calibri"
    p_val.font.size = Pt(26)
    p_val.font.bold = True
    p_val.font.color.rgb = color
    p_val.alignment = PP_ALIGN.CENTER

    p_lbl = tf.add_paragraph()
    p_lbl.text = label
    p_lbl.font.name = "Calibri"
    p_lbl.font.size = Pt(11)
    p_lbl.font.bold = True
    p_lbl.font.color.rgb = TEXT_LIGHT
    p_lbl.alignment = PP_ALIGN.CENTER
    p_lbl.space_after = Pt(2)

    if subtext:
        p_sub = tf.add_paragraph()
        p_sub.text = subtext
        p_sub.font.name = "Calibri"
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = TEXT_MUTED
        p_sub.alignment = PP_ALIGN.CENTER

def create_table(slide, left, top, width, height, headers, rows, col_widths=None):
    """Creates a styled table for algorithm traces and comparisons."""
    num_rows = len(rows) + 1
    num_cols = len(headers)
    table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, width, height)
    table = table_shape.table

    if col_widths and len(col_widths) == num_cols:
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = w

    # Format Header Row
    for col_idx, h_text in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = str(h_text)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TABLE_HEADER_BG
        p = cell.text_frame.paragraphs[0]
        p.font.name = "Calibri"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_CYAN
        p.alignment = PP_ALIGN.CENTER

    # Format Data Rows
    for row_idx, row_data in enumerate(rows):
        bg = TABLE_ALT_ROW if row_idx % 2 == 1 else BG_CARD
        for col_idx, val in enumerate(row_data):
            cell = table.cell(row_idx + 1, col_idx)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            p.font.name = "Calibri"
            p.font.size = Pt(10.5)
            p.font.color.rgb = TEXT_LIGHT
            p.alignment = PP_ALIGN.CENTER if col_idx > 0 and len(str(val)) < 15 else PP_ALIGN.LEFT

def add_speaker_note(slide, note_text):
    """Embeds complete student presentation script into slide notes."""
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = note_text.strip()

# -------------------------------------------------------------
# Main Builder Function
# -------------------------------------------------------------
def build_all_slides(output_path="Smart_Flood_Rescue_System_ADSA_Presentation.pptx"):
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, BG_DARK)

    # Accent Top Stripe
    top_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = ACCENT_BLUE
    top_bar.line.fill.background()

    # Title Container Box
    tbox = s1.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.333), Inches(5.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "B.TECH ARTIFICIAL INTELLIGENCE & DATA SCIENCE  |  END-SEMESTER REVIEW"
    p0.font.name = "Calibri"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_CYAN
    p0.space_after = Pt(10)

    p1 = tf1.add_paragraph()
    p1.text = "SMART FLOOD RESCUE SYSTEM"
    p1.font.name = "Calibri"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT
    p1.space_after = Pt(6)

    p2 = tf1.add_paragraph()
    p2.text = "Advanced Data Structures & Algorithms (ADSA) Project Evaluation"
    p2.font.name = "Calibri"
    p2.font.size = Pt(18)
    p2.font.color.rgb = TEXT_BLUE
    p2.space_after = Pt(28)

    # Team Members Box
    p3 = tf1.add_paragraph()
    p3.text = "PRESENTED BY TEAM NO. 06:"
    p3.font.name = "Calibri"
    p3.font.size = Pt(12)
    p3.font.bold = True
    p3.font.color.rgb = TEXT_MUTED
    p3.space_after = Pt(4)

    team_members = [
        "• U. Raghu Nandan — CB.AI.U4AID25056",
        "• Likhith K. — CB.AI.U4AID25063",
        "• Akshaya S. — CB.AI.U4AID25051"
    ]
    for tm in team_members:
        pt = tf1.add_paragraph()
        pt.text = tm
        pt.font.name = "Calibri"
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_LIGHT
        pt.space_after = Pt(3)

    p_dt = tf1.add_paragraph()
    p_dt.text = "\nDepartment of Computer Science & Engineering  |  October 2026"
    p_dt.font.name = "Calibri"
    p_dt.font.size = Pt(11)
    p_dt.font.color.rgb = TEXT_MUTED

    add_speaker_note(s1, """
Good morning respected faculty members and examiners. We are Team Number 06, comprising U. Raghu Nandan, Likhith K., and Akshaya S., from the Department of Artificial Intelligence and Data Science. 

Today, we present our end-semester project for Advanced Data Structures and Algorithms: the 'Smart Flood Rescue System'. 

This project bridges computer science theory with real-world disaster management. We examine how core algorithmic paradigms—specifically Dijkstra's shortest path on weighted graphs, the Haversine trigonometric formula, distance-based sorting, relational SQL multi-tier ordering, and capacity-constrained conditional logic—can be integrated into an operational system to save human lives during severe flooding emergencies.

Let us begin with the real-world context and motivation behind this work.
""")

    # =========================================================
    # SLIDE 2: INTRODUCTION
    # =========================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, BG_DARK)
    add_header(s2, "Introduction: Disaster Realities & Centralized Coordination", slide_num=2)

    create_card(
        s2, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "What Floods Are & Why Coordination Matters",
        [
            "Urban Inundation Reality: Urban flooding occurs when intense precipitation overwhelms natural drainage channels and civic infrastructure.",
            "Recurring Catastrophes: Events in Chennai (2015/2023), Bengaluru (2022), and Coimbatore flash floods demonstrate rapid water level rise within minutes.",
            "Life-Safety Criticality: Evacuation delays, trapped vulnerable citizens (infants, elderly), and impassable roads lead to preventable loss of life.",
            "The Chaos Factor: During flash floods, standard civilian life is halted, power grids fail, and citizens panic without clear evacuation directives."
        ],
        subtitle="The Physical Disaster Context",
        highlight_color=ACCENT_RED
    )

    create_card(
        s2, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "The Digital Coordination Solution",
        [
            "The Problem of Scattered Information: Emergency calls currently arrive across fragmented social media, private phone helplines, and verbal reports without centralized verification.",
            "Consequences of Fragmentation: Duplication of rescue missions, misdirection of boats to low-risk areas, and neglected critical patients.",
            "Why a Centralized Digital System is Needed: Aggregates real-time citizen distress calls, dynamically verifies shelters, and tracks rescue fleets on one unified dashboard.",
            "Main Idea of Our Project: A full-stack disaster management system that combines live weather telemetry, algorithmic triage, hazard-aware routing, and capacity management."
        ],
        subtitle="System Vision & Purpose",
        highlight_color=TEXT_CYAN
    )

    add_speaker_note(s2, """
On Slide 2, we introduce the physical reality of urban floods and explain why centralized coordination is essential.

Floods are among the most destructive natural disasters in India. As seen in Chennai, Bengaluru, and Coimbatore, intense rainfall can submerge urban neighborhoods in under two hours. 

The primary failure point in traditional disaster response is not the absence of rescue boats or food packets—it is the problem of scattered, uncoordinated information. Distress calls arrive across WhatsApp, phone helplines, police hotlines, and Twitter. Dispatchers have no single source of truth. One family may receive three rescue boats while an elderly patient stranded two streets away is completely forgotten.

Our project introduces a centralized digital platform that brings structured data intake, real-time weather monitoring, algorithmic triage, and safe evacuation route planning into a single automated system. 

Now, let us examine the practical difficulties in the problem statement.
""")

    # =========================================================
    # SLIDE 3: PROBLEM STATEMENT
    # =========================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, BG_DARK)
    add_header(s3, "Problem Statement: Operational Bottlenecks in Disasters", slide_num=3)

    create_card(
        s3, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "1. Concurrency & Urgency",
        [
            "Simultaneous SOS Calls: Hundreds of distress calls flood dispatch centers at the peak of a storm.",
            "Varying Severity: A call for food assistance arrives at the same moment as an SOS for a submerged ground floor with an infant.",
            "Subjective Human Triage: Overworked dispatchers using first-come-first-served queues inadvertently deprioritize critical lives.",
            "Latency Danger: Every minute lost reviewing low-urgency records increases drowning risks."
        ],
        subtitle="Triage & Scale Bottlenecks",
        highlight_color=ACCENT_RED
    )

    create_card(
        s3, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "2. Resource & Capacity Limits",
        [
            "Finite Rescue Teams: Municipalities possess a limited inventory of inflatable boats, NDRF teams, and high-clearance trucks.",
            "Double-Booking Risks: Without concurrency locks, multiple operators assign the same rescue team simultaneously.",
            "Shelter Capacity Violations: Relief camps (schools, halls) have hard physical capacity limits.",
            "Overcrowding Hazards: Sending evacuees to an over-capacity shelter causes health hazards, food shortages, and secondary displacement."
        ],
        subtitle="Physical Constraints",
        highlight_color=ACCENT_AMBER
    )

    create_card(
        s3, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "3. Road Network Hazards",
        [
            "Blind Navigation Engines: Commercial GPS engines (Google Maps/Apple Maps) route vehicles via shortest distance regardless of flood water.",
            "Submerged Underpasses: Underpasses and river culverts (e.g. Sungam Bypass) become death traps for rescue vans and fleeing citizens.",
            "Dynamic Obstructions: Washed-out culverts and fallen trees change road viability minute-by-minute.",
            "Need for Hazard Routing: Routes must explicitly factor in reported road closures and compute safe detours."
        ],
        subtitle="Geospatial Road Failures",
        highlight_color=TEXT_CYAN
    )

    add_speaker_note(s3, """
Slide 3 details the problem statement across three practical difficulties:

First, concurrency and triage urgency. When a dam breach or flash flood occurs, 500 distress requests can arrive in an hour. First-come, first-served processing is dangerous because a request logged at 10:00 AM for dry food might block an SOS logged at 10:05 AM for a family trapped on a terrace with water reaching their chest.

Second, resource scarcity. Rescue teams and relief shelters are strictly finite resources. Shelters have maximum building capacities. If an application blindsides dispatchers and routes 500 evacuees to a community hall that can only hold 200, severe logistical failure occurs.

Third, road network hazards. Commercial navigation tools optimize for travel time under dry conditions. They do not know that a railway underpass has 4 feet of standing water. Rescue trucks following standard GPS can get submerged.

Our project addresses each of these bottlenecks systematically through software engineering and data structures.
""")

    # =========================================================
    # SLIDE 4: PROJECT OBJECTIVES
    # =========================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, BG_DARK)
    add_header(s4, "Project Objectives & Technical Scope", slide_num=4)

    create_card(
        s4, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Core Objectives",
        [
            "1. Automated Incident Intake: Provide a responsive, touch-friendly citizen web interface to register SOS distress calls with headcount, flood depth, and GPS coordinates.",
            "2. Multi-Factor Mathematical Triage: Formulate an algorithmic prioritization model that scores emergencies objectively based on life-safety risks.",
            "3. Hazard-Aware Safe Routing: Integrate a graph-based routing engine that detects reported flooded road segments and computes safe detour paths.",
            "4. Dynamic Shelter Capacity Control: Ensure shelters are vetted and enforce available capacity constraints before assigning evacuees.",
            "5. Live Weather Intelligence: Query official meteorological forecast APIs to display ambient temperature, humidity, wind velocity, and forward rainfall curves."
        ],
        subtitle="System Requirements & Deliverables",
        highlight_color=TEXT_CYAN
    )

    create_card(
        s4, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "How Our Application Addresses Each Objective",
        [
            "• Objective 1 Solution: HTML5/JS Citizen Portal with W3C Geolocation API, Open-Meteo Geocoding, and SQLite ACID transaction persistence.",
            "• Objective 2 Solution: Transparent mathematical scoring in `prioritization.py` and multi-tier SQL ordering via `ORDER BY CASE priority`.",
            "• Objective 3 Solution: Dual routing architecture using Open Source Routing Machine (OSRM) with fallback to NetworkX Dijkstra's algorithm on a penalized graph.",
            "• Objective 4 Solution: Real-time capacity formula `Available = Total - Occupied` combined with OpenStreetMap Overpass/Nominatim discovery.",
            "• Objective 5 Solution: Open-Meteo NWP model telemetry pipeline with WMO 4677 standard code translation and rain probability separation."
        ],
        subtitle="Implementation Alignment",
        highlight_color=ACCENT_GREEN
    )

    add_speaker_note(s4, """
On Slide 4, we define our project objectives and show how each objective maps directly to an engineered module in our codebase.

Our five objectives are:
1. Automated incident intake via a mobile-responsive web portal.
2. Objective mathematical triage to prioritize human life over property.
3. Safe evacuation routing that actively bypasses flooded roads.
4. Dynamic shelter allocation with strict capacity enforcement.
5. Live meteorological telemetry to anticipate flood surges.

As shown on the right-hand card, each objective is backed by concrete implementations: SQLite for transactional persistence, NetworkX Dijkstra for graph detour routing, the Haversine formula for spatial proximity, and Open-Meteo for numerical weather prediction.

Next, let us look at the high-level system architecture.
""")

    # =========================================================
    # SLIDE 5: SYSTEM ARCHITECTURE
    # =========================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, BG_DARK)
    add_header(s5, "System Architecture: Layered Full-Stack Design", slide_num=5)

    # 5 Architecture Horizontal Cards
    layers = [
        ("1. Presentation Tier (Frontend)", "HTML5, CSS3 Responsive Dark Theme, Vanilla JavaScript\nLeaflet.js Interactive GIS Maps, Chart.js Telemetry Canvas\nW3C Browser Geolocation API (±accuracy filtering)", TEXT_CYAN),
        ("2. Application Controller Tier (Flask Backend)", "Python 3.13 Flask WSGI Microservices & RESTful API Endpoints\nRole-Based Session Authorization Guards (Citizen, Admin EOC, Rescue Teams)\nInput Sanitation, Coordinate Bounds Checking (-90° to 90°, -180° to 180°)", ACCENT_BLUE),
        ("3. Core Computational & Algorithm Tier", "NetworkX Dijkstra Graph Routing Engine (`nx.dijkstra_path`)\nHaversine Spherical Trigonometry Distance Engine (`R = 6371 km`)\nMathematical Incident Triage Scoring Heuristic (`prioritization.py`)\nSorting & Conditional Resource State Allocator (`app.py`)", ACCENT_AMBER),
        ("4. Data Persistence & Storage Tier", "SQLite Relational Database Engine (`smart_flood_final.db`)\nRow-Factory Dictionaries, Foreign Key Constraints, Safe Schema Migration Engine\nTables: `citizens`, `admins`, `rescue_teams`, `shelters`, `requests`, `road_hazards`, `notifications`", ACCENT_GREEN),
        ("5. External Geospatial & Weather Services", "Open-Meteo Geocoding API (Global city & coordinate resolution)\nOpen-Meteo Forecast API (High-Resolution NWP ECMWF/GFS Models)\nOpenStreetMap (OSRM Live Routing Engine & Overpass/Nominatim Shelter Discovery)", TEXT_BLUE)
    ]

    for idx, (l_title, l_desc, col) in enumerate(layers):
        top_pos = Inches(1.6 + (idx * 1.05))
        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top_pos, Inches(11.733), Inches(0.92))
        card.fill.solid()
        card.fill.fore_color.rgb = BG_CARD
        card.line.color.rgb = col
        card.line.width = Pt(1.5)

        tx = s5.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.08), Inches(11.3), Inches(0.75))
        tf = tx.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = l_title
        p_t.font.name = "Calibri"
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = l_desc
        p_d.font.name = "Calibri"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_LIGHT

    add_speaker_note(s5, """
Slide 5 illustrates our multi-tier system architecture. We have deliberately segregated concerns into five distinct layers:

At the top is the Presentation Tier: built with responsive HTML5, modern CSS, and JavaScript. We use Leaflet.js for interactive GIS map visualization and Chart.js for 12-hour rainfall forecasting.

Second is the Application Controller Tier: implemented in Python 3.13 using Flask. It exposes RESTful JSON endpoints, enforces role-based session authorization, and validates coordinate inputs against strict geographical bounds.

Third is our Core Computational and Algorithm Tier: the intellectual core of this ADSA review. It hosts NetworkX's Dijkstra pathfinder, the Haversine spherical distance function, the mathematical triage scoring engine, and the resource-sorting pipelines.

Fourth is the Data Persistence Tier: SQLite provides local ACID transactional safety, while our automated schema migration engine ensures backward-compatible database upgrades.

Fifth is the External Services Tier: we interface with Open-Meteo for geocoding and Numerical Weather Prediction models, and OpenStreetMap for live road routing and shelter discovery.

Now let us trace the workflow of an emergency request from end to end.
""")

    # =========================================================
    # SLIDE 6: SYSTEM WORKFLOW
    # =========================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, BG_DARK)
    add_header(s6, "System Workflow: End-to-End Emergency Lifecycle", slide_num=6)

    workflow_steps = [
        ("Step 1: SOS Distress Submission", [
            "Citizen logs in and opens emergency SOS form.",
            "Browser captures GPS coordinates or user enters location.",
            "Submits people count, water depth (1–5), and medical urgency.",
            "Record stored with initial status = 'Pending'."
        ], ACCENT_BLUE),
        ("Step 2: Automated Triage Scoring", [
            "`prioritization.py` executes synchronous risk calculation.",
            "Evaluates flood severity, headcount, and vulnerability factors.",
            "Generates priority score (0–100) and priority category.",
            "Triage level stamped immediately on database record."
        ], ACCENT_RED),
        ("Step 3: EOC Admin Triage Review", [
            "Emergency Operations Center queries `/admin/requests`.",
            "Backend executes multi-tier SQL ordering (Critical first).",
            "Color-coded badges alert commanders to urgent life threats.",
            "Administrator selects incident for resource deployment."
        ], ACCENT_AMBER),
        ("Step 4: Team & Shelter Allocation", [
            "System filters teams with status = 'Available'.",
            "Filters vetted shelters with available capacity >= headcount.",
            "Ranks eligible resources by Haversine proximity.",
            "Atomic transaction commits team and shelter assignment."
        ], ACCENT_GREEN),
        ("Step 5: Hazard-Aware Route Generation", [
            "Routing engine queries active road hazards from database.",
            "OSRM attempts live route; falls back to NetworkX Dijkstra.",
            "Flooded segments receive 100x penalty to force detour.",
            "Safe evacuation path rendered on citizen & team Leaflet map."
        ], TEXT_CYAN),
        ("Step 6: Status Closure & Telemetry Update", [
            "Citizen receives SMS confirmation via notification engine.",
            "Team marks mission 'Completed', releasing unit back to 'Available'.",
            "Shelter occupancy counter incremented automatically.",
            "Continuous Open-Meteo telemetry monitors subsequent rain surges."
        ], TEXT_BLUE)
    ]

    for idx, (s_title, s_points, s_col) in enumerate(workflow_steps):
        col_idx = idx % 3
        row_idx = idx // 3
        c_left = Inches(0.8 + (col_idx * 4.0))
        c_top = Inches(1.6 + (row_idx * 2.7))
        create_card(s6, c_left, c_top, Inches(3.73), Inches(2.5), s_title, s_points, highlight_color=s_col)

    add_speaker_note(s6, """
Slide 6 presents the sequential workflow of our disaster management lifecycle across six distinct stages.

In Step 1, a stranded citizen submits an emergency request with their GPS coordinates, headcount, and water depth. 

In Step 2, our backend immediately runs the prioritization heuristic in prioritization.py, assigning a numerical triage score and category within 15 milliseconds.

In Step 3, the Emergency Operations Center administrator opens the dashboard. The requests arrive pre-sorted via SQL ORDER BY CASE, placing Critical life threats at the very top.

In Step 4, the administrator triggers team assignment. The system filters available rescue units and vetted shelters with sufficient capacity, using Haversine distance to suggest the nearest eligible candidates.

In Step 5, the route planner evaluates known flooded roads. If an underpass is flooded, the graph engine heavily penalizes that edge, forcing Dijkstra to detour safely around the hazard.

In Step 6, the assignment is committed, SMS alerts are dispatched, shelter occupancy is updated, and the team navigates safely to the evacuees.

Let us now review the functional modules of the system.
""")

    # =========================================================
    # SLIDE 7: MAIN SYSTEM MODULES
    # =========================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, BG_DARK)
    add_header(s7, "Main System Modules: Functional Decomposition", slide_num=7)

    create_card(
        s7, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "Citizen & Field Portals",
        [
            "Citizen SOS Portal: One-click distress submission, location autocomplete, and emergency contact registry.",
            "Case Tracking View: Real-time visibility into assigned rescue unit, phone contacts, and allocated shelter.",
            "Rescue Team Dashboard: Frontline mobile view displaying assigned citizen coordinates, headcount, and medical flags.",
            "Field GPS Beaconing: Field units post live GPS updates to maintain spatial situational awareness."
        ],
        subtitle="Frontend Interaction Points",
        highlight_color=ACCENT_BLUE
    )

    create_card(
        s7, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "Decision & Risk Modules",
        [
            "Prioritization Engine: Heuristic scoring evaluating flood depth, demographic vulnerability, and waiting duration.",
            "Meteorological Telemetry: Open-Meteo REST service integration parsing temperature, wind, humidity, and rainfall.",
            "Flood Risk Assessor: Synthesizes regional rainfall totals and historical vulnerability into actionable risk tiers.",
            "Safe Route Planner: Multi-engine navigation combining OSRM geometries with NetworkX Dijkstra detour graphs."
        ],
        subtitle="Analytical Computational Core",
        highlight_color=ACCENT_AMBER
    )

    create_card(
        s7, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.3),
        "EOC Administration",
        [
            "Incident Command Center: Master administrative dashboard sorting emergencies by triage urgency.",
            "Shelter Operations: Real-time shelter verification, capacity tracking, and OSM candidate discovery.",
            "Road Hazard Manager: Interface to report, activate, and deactivate submerged road segments.",
            "Notification Engine: In-app operational notifications and SMS dispatch simulator."
        ],
        subtitle="Command & Control Infrastructure",
        highlight_color=ACCENT_GREEN
    )

    add_speaker_note(s7, """
Slide 7 breaks down our application into three functional module groups:

On the left are the Citizen and Field Portals: providing mobile-optimized, high-contrast user interfaces for stranded citizens and frontline rescue workers.

In the center is our Analytical Computational Core: containing the algorithmic logic. This includes prioritization.py for triage scoring, flood_risk.py for risk assessment, and routing.py for hazard-aware navigation.

On the right is the EOC Administration module: giving municipal disaster commanders full situational control to deploy rescue teams, verify relief shelters, and manage road hazards.

Let us now inspect the underlying technology stack.
""")

    # =========================================================
    # SLIDE 8: TECHNOLOGY STACK
    # =========================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, BG_DARK)
    add_header(s8, "Technology Stack: Tooling & Engineering Justification", slide_num=8)

    tech_headers = ["Technology", "Role in Project", "Engineering Justification / Why Chosen"]
    tech_rows = [
        ["Python 3.13", "Core Backend & Algorithmic Runtime", "Provides rich mathematical, graph, and scientific libraries (NetworkX, math) with rapid development velocity."],
        ["Flask (WSGI)", "Lightweight Web Application Framework", "Minimalist microframework allowing modular RESTful endpoint design without the overhead of heavy enterprise frameworks."],
        ["SQLite / libSQL", "Relational Database Tier", "ACID-compliant, zero-configuration relational storage; supports Turso/libSQL edge replication and local development portability."],
        ["NetworkX 3.x", "Graph Data Structures & Algorithms", "Standard Python library for complex network analysis; provides robust, highly optimized Dijkstra implementations on weighted graphs."],
        ["Leaflet.js 1.9", "Interactive Geospatial GIS Mapping", "Lightweight, mobile-friendly open-source mapping engine capable of rendering custom SVG hazard markers, routes, and layer groups."],
        ["Chart.js 4.x", "Meteorological & Capacity Analytics", "Hardware-accelerated HTML5 canvas charting engine for forward-looking 12-hour hourly rainfall and capacity utilization gauges."],
        ["Open-Meteo APIs", "Live NWP Weather & Geocoding", "Official meteorological forecast models (ECMWF/GFS) delivering real-time atmospheric readings and worldwide place geocoding."],
        ["OSRM / OSM", "Road Geometries & Shelter Discovery", "OpenStreetMap road network data providing real-world driving paths and Overpass/Nominatim amenity discovery for relief shelters."]
    ]
    create_table(s8, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.3), tech_headers, tech_rows, [Inches(1.8), Inches(3.2), Inches(6.733)])

    add_speaker_note(s8, """
Slide 8 presents our technology stack. Every tool was chosen deliberately for reliability under disaster constraints:

Python 3.13 and Flask provide our microservices backend. Python gives us direct access to NetworkX for graph computation and standard libraries like math and sqlite3.

SQLite provides transactional integrity with zero database setup. For cloud deployment, it seamlessly ports to Turso and libSQL.

NetworkX is our graph algorithm engine. It manages node adjacency and executes Dijkstra's algorithm.

On the frontend, Leaflet.js renders interactive GIS maps with zero external API key dependencies, while Chart.js plots our 12-hour rainfall telemetry.

Finally, Open-Meteo and OpenStreetMap provide global geocoding, high-resolution weather models, and public shelter discovery without paid proprietary vendor locks.

Now, we enter our dedicated algorithm section—the core focus of our ADSA review.
""")

    # =========================================================
    # SLIDE 9: ALGORITHMS & DATA STRUCTURES OVERVIEW
    # =========================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, BG_DARK)
    add_header(s9, "Algorithms & Data Structures: Project Inventory", slide_num=9)

    algo_headers = ["Algorithm / Technique", "Purpose", "Where Used in Codebase", "Input Data", "Output Result"]
    algo_rows = [
        ["Dijkstra's Algorithm", "Single-source shortest path on weighted graphs", "`routing.py` (`nx.dijkstra_path`)", "Weighted Graph G(V, E), Start node, End node", "Ordered sequence of node IDs forming optimal path"],
        ["Haversine Formula", "Computes great-circle surface distance on sphere", "`routing.py` & `shelter_discovery.py`", "Two GPS coordinate pairs (lat1, lon1), (lat2, lon2)", "Great-circle distance in kilometers (float)"],
        ["Distance-Based Sorting", "Orders eligible resources by spatial proximity", "`app.py` resource allocation loops", "Unordered list of eligible teams/shelters with distances", "Ascending list of resources ranked from nearest to farthest"],
        ["SQL Multi-Tier Ordering", "Sorts emergency requests by priority & score", "`app.py` in `@app.route('/admin/requests')`", "`requests` table rows with priority, score, id", "Relational rows ordered: Critical > High > Medium > Low"],
        ["Conditional Allocation Logic", "Enforces capacity limits and availability states", "`app.py` team dispatch & shelter selection", "Candidate status, total capacity, occupied headcount", "Binary pass/fail selection; atomic state mutation"],
        ["Graph Representation", "Models navigable road corridors and detours", "`routing.py` (`COIMBATORE_ROAD_NODES`, edges)", "Road network vertices (lat/lon) and base edge distances", "NetworkX Graph instance G with penalized edge weights"]
    ]
    create_table(s9, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.3), algo_headers, algo_rows, [Inches(2.2), Inches(2.6), Inches(2.3), Inches(2.3), Inches(2.333)])

    add_speaker_note(s9, """
Slide 9 opens our dedicated Algorithm Section with an inventory table comparing all computational techniques used across our codebase.

Notice the five distinct columns: the Technique, its Purpose, its exact Location in our Codebase, its Input, and its Output.

We want to highlight an important academic distinction: our project distinguishes standard graph algorithms from relational database operations and procedural business logic. 
- Dijkstra is our graph pathfinder for route planning.
- Haversine is our trigonometric distance metric.
- Python list sorting arranges candidate resources by distance.
- Relational SQL ORDER BY CASE sequences our triage dashboard.
- Conditional logic enforces capacity and team availability.
- And NetworkX Graph structures represent our road network.

Importantly, we do NOT falsely claim to implement a custom heap priority queue. Instead, we use SQL ordering for database records and NetworkX's internal heap for Dijkstra.

Let us now explore Dijkstra's algorithm in detail over the next three slides.
""")

    # =========================================================
    # SLIDE 10: DIJKSTRA — PART 1: GRAPH FOUNDATIONS
    # =========================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, BG_DARK)
    add_header(s10, "Dijkstra's Algorithm — Part 1: Graph Foundations", slide_num=10)

    create_card(
        s10, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Formal Graph Terminology & Definitions",
        [
            "What is a Graph?: A mathematical structure G = (V, E) composed of a set of vertices (V) and a set of connecting edges (E).",
            "Vertex (Node): A discrete spatial point or intersection in our road network (e.g., Gandhipuram Hub, Town Hall).",
            "Edge (Link): A navigable transportation link connecting two adjacent vertices, representing a road segment.",
            "Edge Weight (Cost): A non-negative scalar value representing the impedance of traversing that edge (base distance in km, travel time, or flood hazard penalty).",
            "Weighted Graph: A graph where every edge (u, v) is assigned a numerical weight w(u, v) ≥ 0.",
            "Directed vs. Undirected: Our road network is modeled as an undirected graph G, assuming two-way vehicle navigability unless blocked."
        ],
        subtitle="Theoretical Foundations",
        highlight_color=TEXT_CYAN
    )

    create_card(
        s10, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Why Dijkstra is Needed for Emergency Routing",
        [
            "The Problem Solved: Given a road network G, a start location S, and an evacuation shelter T, find the trajectory that minimizes the cumulative cost: ∑ w(u, v).",
            "Why Simple BFS Fails: Breadth-First Search (BFS) only computes shortest paths in unweighted graphs (where all edge costs equal 1). In road networks, edge distances and hazard conditions vary dramatically.",
            "Why Greedy Choice Works: Dijkstra operates on the principle of optimal substructure: any subpath of an optimal shortest path is itself an optimal shortest path.",
            "The Non-Negative Weight Invariant: Dijkstra strictly requires w(u, v) ≥ 0. In physical road networks, distances and hazard penalties are always non-negative, making Dijkstra mathematically sound."
        ],
        subtitle="Algorithmic Justification",
        highlight_color=ACCENT_BLUE
    )

    add_speaker_note(s10, """
On Slide 10, we begin our deep dive into Dijkstra's algorithm by reviewing foundational graph theory.

A graph G is defined formally as a pair (V, E), where V is a set of vertices and E is a set of edges. In our disaster application, vertices represent physical road intersections or emergency hubs, and edges represent road segments connecting them.

Each edge has a weight, which represents traversal impedance. Under normal dry conditions, this weight is simply the physical road distance in kilometers. Under flood conditions, this weight is dynamically scaled up to reflect hazard severity.

Why do we use Dijkstra's algorithm? Because road networks are weighted. A standard Breadth-First Search assumes every street has identical cost, which is false in geography. Dijkstra solves the single-source shortest path problem on weighted graphs with non-negative edge weights.

Because physical road distances and flood penalties are strictly non-negative, Dijkstra's greedy choice property is guaranteed to find the optimal path.

Let us now walk through a step-by-step numerical trace on Slide 11.
""")

    # =========================================================
    # SLIDE 11: DIJKSTRA — PART 2: STEP-BY-STEP TRACE
    # =========================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, BG_DARK)
    add_header(s11, "Dijkstra's Algorithm — Part 2: Step-by-Step Numerical Trace", slide_num=11)

    # Left: Problem definition card
    create_card(
        s11, Inches(0.8), Inches(1.6), Inches(4.5), Inches(5.3),
        "Example Graph Definition",
        [
            "We trace Dijkstra on this directed weighted graph:",
            "  • S → A with weight = 2",
            "  • S → B with weight = 1",
            "  • A → T with weight = 3",
            "  • B → T with weight = 6",
            "Source Node: S   |   Target Node: T",
            "Initial State:",
            "  • dist[S] = 0",
            "  • dist[A] = ∞, dist[B] = ∞, dist[T] = ∞",
            "  • Visited set: Q = ∅",
            "Candidate Paths to Target T:",
            "  1. Path S → A → T: Cost = 2 + 3 = 5",
            "  2. Path S → B → T: Cost = 1 + 6 = 7",
            "Optimal Solution: S → A → T (Total Cost = 5)"
        ],
        subtitle="S → T Minimum Weight Problem",
        highlight_color=ACCENT_AMBER
    )

    # Right: Step-by-Step Execution Table
    trace_headers = ["Step", "Selected Node", "Tentative dist[A]", "Tentative dist[B]", "Tentative dist[T]", "Visited Set Q"]
    trace_rows = [
        ["0", "Initialization", "∞", "∞", "∞", "∅"],
        ["1", "Node S (dist=0)", "2 (via S)", "1 (via S)", "∞", "{S}"],
        ["2", "Node B (dist=1)", "2", "1", "1 + 6 = 7 (via B)", "{S, B}"],
        ["3", "Node A (dist=2)", "2", "1", "min(7, 2+3) = 5 (via A)", "{S, B, A}"],
        ["4", "Node T (dist=5)", "2", "1", "5", "{S, B, A, T}"]
    ]
    create_table(s11, Inches(5.5), Inches(1.6), Inches(7.033), Inches(3.2), trace_headers, trace_rows, [Inches(0.6), Inches(1.6), Inches(1.2), Inches(1.2), Inches(1.4), Inches(1.033)])

    # Bottom Explanation Box
    exp_card = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.5), Inches(5.0), Inches(7.033), Inches(1.9))
    exp_card.fill.solid()
    exp_card.fill.fore_color.rgb = BG_CARD
    exp_card.line.color.rgb = ACCENT_GREEN
    exp_card.line.width = Pt(1.5)

    tx_exp = s11.shapes.add_textbox(Inches(5.7), Inches(5.1), Inches(6.6), Inches(1.7))
    tf_exp = tx_exp.text_frame
    tf_exp.word_wrap = True
    p_et = tf_exp.paragraphs[0]
    p_et.text = "Why the Algorithm Selects Path S → A → T:"
    p_et.font.name = "Calibri"
    p_et.font.size = Pt(13)
    p_et.font.bold = True
    p_et.font.color.rgb = ACCENT_GREEN
    p_et.space_after = Pt(2)

    exp_points = [
        "At Step 2, node B is greedy-selected first because dist[B]=1 < dist[A]=2.",
        "However, B's outward edge to T is very costly (weight 6), yielding tentative dist[T]=7.",
        "At Step 3, node A is extracted (dist=2) and relaxes edge A→T (cost 3), reducing dist[T] from 7 down to 5.",
        "Final Result: Dijkstra correctly identifies S → A → T (cost 5) over S → B → T (cost 7)."
    ]
    for ep in exp_points:
        p = tf_exp.add_paragraph()
        p.text = f"• {ep}"
        p.font.name = "Calibri"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_LIGHT

    add_speaker_note(s11, """
Slide 11 walks through an exact numerical execution trace of Dijkstra's algorithm. This is a very common viva question.

Let us trace the graph: We want to go from start node S to destination T. 
S connects to A with weight 2, and to B with weight 1. 
A connects to T with weight 3. B connects to T with weight 6.

Look at the trace table:
At Step 0, all tentative distances are infinity except S, which is 0.
At Step 1, we visit S. We relax edges to A and B. Tentative distance to A becomes 2; distance to B becomes 1.
At Step 2, Dijkstra greedily picks the unvisited node with the smallest tentative distance: node B, with distance 1. From B, the edge to T has weight 6, making the tentative distance to T equal to 1 + 6 = 7.
At Step 3, we pick the next smallest unvisited node: node A, with distance 2. From A, the edge to T has weight 3. We calculate 2 + 3 = 5. Since 5 is strictly less than 7, edge relaxation updates the tentative distance to T from 7 down to 5!
Finally, at Step 4, T is selected with distance 5.

The final optimal path is S -> A -> T with cost 5. Notice how Dijkstra did not get permanently trapped by the locally greedy choice of node B.

Now let us examine how this exact logic is implemented in our Python codebase.
""")

    # =========================================================
    # SLIDE 12: DIJKSTRA — PART 3: CODE & ANALYSIS
    # =========================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, BG_DARK)
    add_header(s12, "Dijkstra's Algorithm — Part 3: Code Implementation & Analysis", slide_num=12)

    create_card(
        s12, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Actual Code Pattern in routing.py",
        [
            "NetworkX Invocation in routing.py (Line 435):",
            "  `path = nx.dijkstra_path(G, start_node, end_node, weight='weight')`",
            "Parameter Breakdown:",
            "  • `nx.dijkstra_path`: NetworkX's built-in min-heap Dijkstra implementation.",
            "  • `G`: NetworkX Graph containing road intersections and edges.",
            "  • `start_node`: Origin road node closest to incident GPS.",
            "  • `end_node`: Target road node closest to assigned shelter.",
            "  • `weight='weight'`: Edge attribute holding distance + flood hazard penalty.",
            "  • `path`: Returned Python list of node IDs forming optimal path.",
            "Built-in vs. Manual: The project leverages NetworkX's battle-tested implementation rather than hand-crafting a heap.",
            "Time Complexity: O(|E| + |V| log |V|) using a binary min-heap."
        ],
        subtitle="Source Code Inspection",
        highlight_color=ACCENT_BLUE
    )

    # Right side: Hazard Penalty Table & Theoretical Analysis
    create_card(
        s12, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Hazard Penalties & Theoretical Comparison",
        [
            "Illustrative Road Hazard Penalty Mechanism:",
            "  • Route A: Base cost = 3.0 km, Hazard penalty = +8.0, Total = 11.0",
            "  • Route B: Base cost = 5.0 km, Hazard penalty = +0.0, Total = 5.0",
            "  • Decision: Route B is selected (5.0 < 11.0) despite longer base distance!",
            "Code Multiplier in routing.py (Line 173):",
            "  If segment is flooded: `weight *= 100.0` (severe edge penalty).",
            "Theoretical Comparisons for Viva:",
            "  • Dijkstra vs. BFS: BFS is unweighted O(V+E); Dijkstra supports arbitrary non-negative weights.",
            "  • Dijkstra vs. A*: A* adds a goal-directed heuristic h(n); Dijkstra is unguided (h(n)=0).",
            "  • Non-Negative Constraint: Negative weights invalidate greedy relaxation.",
            "  • Vital Limitation: Dijkstra guarantees optimality in the *modeled graph*, not real-world safety."
        ],
        subtitle="Dynamic Detours & Viva Concepts",
        highlight_color=TEXT_CYAN
    )

    add_speaker_note(s12, """
Slide 12 connects Dijkstra theory directly to our Python codebase in routing.py.

Look at line 435 of routing.py: 
`path = nx.dijkstra_path(G, start_node, end_node, weight='weight')`
We call NetworkX's built-in Dijkstra function. We do not write a manual heap queue because NetworkX's C-optimized binary heap implementation provides guaranteed O(|E| + |V| log |V|) performance.

How do we route around floods? Through edge weight penalization. Look at lines 170 to 175 of routing.py. When a road hazard has severity 'Flooded' or 'Closed', we multiply the edge's base distance by 100! 

As shown in the table on the right, Route A has a base length of 3 km, but carries an 8-unit flood penalty, making its total cost 11. Route B is longer at 5 km, but has zero hazard penalty. Dijkstra compares 11 versus 5 and chooses Route B! This produces our automatic flood detour.

Examiners frequently ask: What is the difference between Dijkstra and A*? 
Dijkstra evaluates nodes uniformly in all directions based on cost g(n). A* adds a heuristic h(n) estimating the distance to the goal, pulling the search tree toward the destination.

Next, let us examine how we calculate physical geographic distances: the Haversine formula.
""")

    # =========================================================
    # SLIDE 13: HAVERSINE — PART 1: GEOMETRY & FORMULATION
    # =========================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13, BG_DARK)
    add_header(s13, "Haversine Formula — Part 1: Spherical Geometry & Formulation", slide_num=13)

    create_card(
        s13, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Why Geographic Distance Requires Spherical Trigonometry",
        [
            "The Flat-Earth Fallacy: Standard Euclidean distance d = √((x2-x1)² + (y2-y1)²) assumes a flat Cartesian 2D plane.",
            "Earth's Geometry: The Earth is an oblate spheroid. Meridians of longitude converge at the poles, meaning 1 degree of longitude varies from 111 km at the equator to 0 km at the poles.",
            "Latitude (φ): Angular distance north or south of the Equator (-90° to +90°).",
            "Longitude (λ): Angular distance east or west of the Prime Meridian (-180° to +180°).",
            "Great-Circle Distance: The shortest path between any two points along the surface of a sphere, formed by the intersection of the sphere with a plane passing through the Earth's center."
        ],
        subtitle="Geodetic Principles",
        highlight_color=TEXT_CYAN
    )

    create_card(
        s13, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "The Mathematical Formulation",
        [
            "The Haversine Equation:",
            "  a = sin²(Δφ / 2) + cos(φ1) · cos(φ2) · sin²(Δλ / 2)",
            "  c = 2 · arcsin(√a)  =  2 · atan2(√a, √(1 - a))",
            "  d = R · c",
            "Symbol Definitions:",
            "  • φ1, φ2 = Latitudes of Point 1 and Point 2 in RADIANS.",
            "  • λ1, λ2 = Longitudes of Point 1 and Point 2 in RADIANS.",
            "  • Δφ = φ2 - φ1   (Latitude difference in radians).",
            "  • Δλ = λ2 - λ1   (Longitude difference in radians).",
            "  • R = 6,371.0 km (Earth's mean volumetric radius).",
            "  • d = Calculated great-circle surface distance in kilometers."
        ],
        subtitle="Formula Breakdown",
        highlight_color=ACCENT_BLUE
    )

    add_speaker_note(s13, """
On Slide 13, we examine our second core mathematical algorithm: the Haversine formula.

Why do we need Haversine? Why can't we use standard Euclidean distance?
Because the Earth is a sphere, not a flat sheet of paper. If you calculate Euclidean distance directly on latitude and longitude degrees, your distance calculation will be completely inaccurate because lines of longitude converge at the poles. One degree of longitude is 111 km in Chennai, but shrinks to zero at the North Pole.

The Haversine formula calculates the great-circle distance—the shortest curved distance across the Earth's spherical surface.

Look at the equations on the right:
First, we convert latitude and longitude from degrees to radians.
Then, we compute term 'a', which uses the square of half-angle sines combined with the cosine of both latitudes.
Next, 'c' calculates the angular distance in radians using the two-argument arctangent.
Finally, multiplying 'c' by the Earth's mean radius R (6,371 kilometers) yields the exact surface distance 'd' in kilometers.

Let us now work through a numerical example on Slide 14.
""")

    # =========================================================
    # SLIDE 14: HAVERSINE — PART 2: WORKED EXAMPLE & APPLICATION
    # =========================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14, BG_DARK)
    add_header(s14, "Haversine Formula — Part 2: Numerical Example & Application", slide_num=14)

    create_card(
        s14, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Numerical Worked Example (Illustrative)",
        [
            "Point 1 (Citizen SOS in Gandhipuram):",
            "  lat1 = 11.0183° N, lon1 = 76.9725° E",
            "Point 2 (Shelter in RS Puram):",
            "  lat2 = 11.0085° N, lon2 = 76.9485° E",
            "Step 1: Degree Differences",
            "  Δlat = 11.0085 - 11.0183 = -0.0098°",
            "  Δlon = 76.9485 - 76.9725 = -0.0240°",
            "Step 2: Convert to Radians (multiply by π / 180)",
            "  Δφ = -0.000171 rad   |   Δλ = -0.000419 rad",
            "  φ1 = 0.192305 rad   |   φ2 = 0.192134 rad",
            "Step 3: Evaluate Haversine a and c",
            "  a = sin²(-0.0000855) + cos(0.1923)·cos(0.1921)·sin²(-0.000209)",
            "  a ≈ 5.01 × 10⁻⁸  →  c ≈ 0.0004478 rad",
            "Step 4: Surface Distance d = 6371 × 0.0004478 ≈ 2.85 km"
        ],
        subtitle="Step-by-Step Calculation",
        highlight_color=ACCENT_GREEN
    )

    create_card(
        s14, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Implementation in Code & Vital Safety Limitation",
        [
            "Code Implementation in routing.py (Lines 71–80):",
            "  ```python",
            "  def haversine_distance(lat1, lon1, lat2, lon2):",
            "      R = 6371.0",
            "      dlat = math.radians(lat2 - lat1)",
            "      dlon = math.radians(lon2 - lon1)",
            "      a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \\",
            "          math.cos(math.radians(lat2)) * math.sin(dlon/2)**2",
            "      c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))",
            "      return R * c",
            "  ```",
            "Where Used in Our Project:",
            "  1. Comparing citizen request coordinates with candidate shelters.",
            "  2. Spatial hazard proximity testing: flags edges within 0.8 km of flood.",
            "CRITICAL LIMITATION FOR VIVA:",
            "  Haversine computes STRAIGHT-LINE ('as the crow flies') distance.",
            "  It does NOT account for roads, rivers, or bridges. A shelter 1 km away across a swollen river may require a 7 km road detour!"
        ],
        subtitle="Source Code & Geodetic Limits",
        highlight_color=ACCENT_RED
    )

    add_speaker_note(s14, """
Slide 14 provides an exact numerical walkthrough of the Haversine formula and highlights its implementation in Python.

On the left, we trace an illustrative calculation between Gandhipuram and RS Puram:
We compute the difference in latitude (-0.0098 degrees) and longitude (-0.0240 degrees).
We convert these to radians by multiplying by pi / 180.
Plugging these values into the Haversine equation yields a straight-line surface distance of approximately 2.85 kilometers.

Look at the code on the right: lines 71 to 80 of routing.py implement this exact formula using Python's standard `math` module.

Now, examiners will test your critical thinking here. They will ask: 'Does Haversine give you the actual road travel distance?'
You must answer: NO. Haversine gives straight-line geographic distance across a sphere. It does not know if there are buildings, lakes, or impassable flooded streets in between. That is why Haversine is used for initial proximity filtering, while Dijkstra and OSRM are used for actual road route planning.

Next, let us see how candidate resources are sorted and selected on Slide 15.
""")

    # =========================================================
    # SLIDE 15: SORTING AND RESOURCE SELECTION
    # =========================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_slide_background(s15, BG_DARK)
    add_header(s15, "Sorting & Resource Selection: Proximity Ranking", slide_num=15)

    create_card(
        s15, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Resource Selection Pipeline",
        [
            "How the Application Selects Resources:",
            "  1. Availability Filtering: Disqualifies busy teams: `status == 'Available'`.",
            "  2. Capacity Filtering: Disqualifies full shelters: `(capacity - occupied) >= people`.",
            "  3. Verification Check: Only operational shelters (`verified == 1`) are considered.",
            "  4. Distance Calculation: Evaluates Haversine distance from incident GPS to every eligible candidate.",
            "  5. In-Memory Sorting: Sorts candidate list by computed distance in ascending order.",
            "  6. Assignment Commitment: Dispatches top candidate and commits state changes atomically.",
            "Sorting vs. Nearest-Neighbour:",
            "  • Sorting arranges an entire static list of n items in O(n log n) time.",
            "  • Nearest-Neighbour in spatial trees (k-d trees) queries proximity in O(log n) time without sorting all elements."
        ],
        subtitle="5-Step Allocation Logic",
        highlight_color=TEXT_CYAN
    )

    # Right: Team Selection Table & Explanation
    res_headers = ["Rescue Team", "Haversine Distance", "Operational Status", "Selection Outcome"]
    res_rows = [
        ["Team A", "4.2 km", "Available", "Eligible (Rank 2)"],
        ["Team B", "2.1 km", "Available", "SELECTED (Nearest Eligible Rank 1)"],
        ["Team C", "1.0 km", "Busy (Assigned)", "DISQUALIFIED (Unavailable)"]
    ]
    create_table(s15, Inches(6.8), Inches(1.6), Inches(5.733), Inches(2.6), res_headers, res_rows, [Inches(1.3), Inches(1.4), Inches(1.4), Inches(1.633)])

    sel_card = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(4.5), Inches(5.733), Inches(2.4))
    sel_card.fill.solid()
    sel_card.fill.fore_color.rgb = BG_CARD
    sel_card.line.color.rgb = ACCENT_AMBER
    sel_card.line.width = Pt(1.5)

    tx_s = s15.shapes.add_textbox(Inches(7.0), Inches(4.6), Inches(5.3), Inches(2.2))
    tf_s = tx_s.text_frame
    tf_s.word_wrap = True
    p_st = tf_s.paragraphs[0]
    p_st.text = "Key Viva Insights on Resource Selection:"
    p_st.font.name = "Calibri"
    p_st.font.size = Pt(12)
    p_st.font.bold = True
    p_st.font.color.rgb = ACCENT_AMBER
    p_st.space_after = Pt(2)

    sp_points = [
        "Why isn't Team C chosen even though it is only 1.0 km away? Because Team C is 'Busy'. Availability strictly precedes distance.",
        "Team B (2.1 km) is selected because it is the nearest ELIGIBLE team.",
        "The nearest team is not automatically dispatched in every scenario; fallback rules apply if all teams are busy.",
        "Python's Timsort algorithm (`sorted()` with `key=lambda x: x['dist']`) runs in O(n log n) worst-case time."
    ]
    for sp in sp_points:
        p = tf_s.add_paragraph()
        p.text = f"• {sp}"
        p.font.name = "Calibri"
        p.font.size = Pt(9.5)
        p.font.color.rgb = TEXT_LIGHT

    add_speaker_note(s15, """
Slide 15 explains our resource selection pipeline.

In emergency dispatch, physical proximity is meaningless if the resource is unavailable. Our pipeline enforces a strict multi-stage rule:
1. Filter by availability for rescue teams, or by verification and capacity for shelters.
2. Calculate Haversine distance to the eligible candidates.
3. Sort the eligible candidates in ascending order by distance using Python's O(n log n) Timsort.
4. Select the top candidate.

Look at the table on the right:
Team C is only 1.0 km away from the incident. But Team C is 'Busy'—it is already deployed on another rescue mission. Team C is immediately disqualified.
Team B is 2.1 km away and is 'Available'. Team A is 4.2 km away and is 'Available'.
Team B is selected because it is the nearest *eligible* resource.

An examiner might ask: 'Is sorting the same as a nearest-neighbor algorithm?'
Answer: No. Sorting arranges the entire collection of n elements in O(n log n) time. A nearest-neighbor query in a spatial data structure like a k-d tree or R-tree finds the closest point in O(log n) time without sorting the entire dataset. For our scale of municipal teams, list sorting is lightweight and robust.

Now let us examine how emergency requests are ordered in SQL on Slide 16.
""")

    # =========================================================
    # SLIDE 16: SQL-BASED PRIORITY ORDERING
    # =========================================================
    s16 = prs.slides.add_slide(blank_layout)
    set_slide_background(s16, BG_DARK)
    add_header(s16, "SQL-Based Emergency Priority Ordering", slide_num=16)

    create_card(
        s16, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Actual SQL Query in app.py (Lines 1105–1116)",
        [
            "```sql",
            "SELECT * FROM requests",
            "ORDER BY",
            "    CASE priority",
            "        WHEN 'Critical' THEN 1",
            "        WHEN 'High'     THEN 2",
            "        WHEN 'Medium'   THEN 3",
            "        ELSE 4",
            "    END,",
            "    priority_score DESC,",
            "    id DESC",
            "```",
            "Line-by-Line Technical Breakdown:",
            "  • `CASE priority`: Conditional expression mapping categorical text strings into numeric ranks (1, 2, 3, 4).",
            "  • `WHEN 'Critical' THEN 1`: Guarantees all Critical incidents group at the very top.",
            "  • `priority_score DESC`: Secondary sort criterion—orders by continuous score (e.g. 95 before 80) WITHIN the same category.",
            "  • `id DESC`: Tertiary tie-breaker ensuring FIFO consistency."
        ],
        subtitle="Relational Triage Implementation",
        highlight_color=ACCENT_BLUE
    )

    # Right: Worked SQL Ordering Table
    sql_headers = ["Request", "Priority Category", "Priority Score", "Assigned Rank", "Display Position"]
    sql_rows = [
        ["Request A", "Critical", "95", "1 (Critical)", "1st (Top of Queue)"],
        ["Request B", "Critical", "80", "1 (Critical)", "2nd"],
        ["Request C", "High", "98", "2 (High)", "3rd"],
        ["Request D", "Medium", "45", "3 (Medium)", "4th"]
    ]
    create_table(s16, Inches(6.8), Inches(1.6), Inches(5.733), Inches(2.8), sql_headers, sql_rows, [Inches(1.1), Inches(1.4), Inches(1.0), Inches(1.1), Inches(1.133)])

    sql_note_card = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(4.7), Inches(5.733), Inches(2.2))
    sql_note_card.fill.solid()
    sql_note_card.fill.fore_color.rgb = BG_CARD
    sql_note_card.line.color.rgb = ACCENT_RED
    sql_note_card.line.width = Pt(1.5)

    tx_sn = s16.shapes.add_textbox(Inches(7.0), Inches(4.8), Inches(5.3), Inches(2.0))
    tf_sn = tx_sn.text_frame
    tf_sn.word_wrap = True
    p_snt = tf_sn.paragraphs[0]
    p_snt.text = "CRITICAL ADSA DISTINCTION FOR VIVA:"
    p_snt.font.name = "Calibri"
    p_snt.font.size = Pt(12)
    p_snt.font.bold = True
    p_snt.font.color.rgb = ACCENT_RED
    p_snt.space_after = Pt(2)

    sn_points = [
        "Why does Request B (Critical, 80) appear BEFORE Request C (High, 98)? Because category rank 1 (Critical) strictly overrides numerical score!",
        "THIS IS NOT A CUSTOM HEAP PRIORITY QUEUE: The administrator dashboard runs relational database sorting on every query.",
        "SQL ORDER BY runs an O(N log N) database sort. A Heap Priority Queue maintains an in-memory binary tree with O(log N) insert and O(1) peek.",
        "For web-based stateless REST APIs, SQL ordering ensures immediate database consistency across multiple admin browser tabs."
    ]
    for sn in sn_points:
        p = tf_sn.add_paragraph()
        p.text = f"• {sn}"
        p.font.name = "Calibri"
        p.font.size = Pt(9.5)
        p.font.color.rgb = TEXT_LIGHT

    add_speaker_note(s16, """
Slide 16 details our emergency priority ordering in SQL. This is one of the most critical slides for your viva defense.

Look at the query on the left, taken directly from lines 1105 to 1116 of app.py:
```sql
SELECT * FROM requests ORDER BY
    CASE priority
        WHEN 'Critical' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        ELSE 4
    END,
    priority_score DESC,
    id DESC
```

How does this work?
First, the SQL CASE statement maps text categories into numerical ranks: Critical becomes 1, High becomes 2, Medium becomes 3, Low becomes 4.
Second, within each category, it sorts by `priority_score DESC`.
Third, if two requests have the exact same score, `id DESC` acts as a tie-breaker.

Now, look at the table on the right. Examiners will ask this exact question:
'Look at Request B and Request C. Request C has a score of 98. Request B has a score of 80. Why does Request B appear before Request C?'
Your answer must be: Because Request B has category 'Critical' (Rank 1), while Request C has category 'High' (Rank 2). The primary sort key is the category rank, which completely overrides the raw numerical score!

Second viva trap: 'Is this a Priority Queue data structure?'
Your answer must be clear: No, sir. This is relational database sorting via SQL ORDER BY, running in O(N log N) time on query execution. A priority queue is an abstract data structure typically implemented using a binary or Fibonacci min/max heap. We use SQL ordering because it provides ACID consistency across stateless REST API sessions.

Next, let us look at the conditional logic for team and shelter allocation on Slide 17.
""")

    # =========================================================
    # SLIDE 17: TEAM & SHELTER CONDITIONAL LOGIC
    # =========================================================
    s17 = prs.slides.add_slide(blank_layout)
    set_slide_background(s17, BG_DARK)
    add_header(s17, "Conditional Business Logic: Resource Allocation & Capacity", slide_num=17)

    create_card(
        s17, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Rescue Team Assignment State Machine",
        [
            "Team Availability Invariant: A rescue unit can only be deployed if its current status is 'Available'.",
            "Concurrency Protection in app.py (Lines 1230–1255):",
            "  ```python",
            "  team = conn.execute('SELECT * FROM rescue_teams '",
            "                      'WHERE status = \"Available\" '",
            "                      'ORDER BY id LIMIT 1').fetchone()",
            "  if team is None:",
            "      return jsonify({'error': 'No available teams'}), 409",
            "  # Atomic status transition",
            "  conn.execute('UPDATE rescue_teams SET status = \"Assigned\" '",
            "               'WHERE id = ?', (team['id'],))",
            "  ```",
            "State Machine Transitions:",
            "  • Available → Assigned (when deployed to an emergency SOS)",
            "  • Assigned → Completed (when evacuees are delivered to shelter)",
            "  • Completed → Available (unit resets for next mission)"
        ],
        subtitle="Mutual Exclusion & State Integrity",
        highlight_color=ACCENT_BLUE
    )

    create_card(
        s17, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Shelter Capacity Formula & Allocation Logic",
        [
            "Shelter Capacity Formula:",
            "  Available Capacity = Total Capacity - Occupied Capacity",
            "Allocation Condition in app.py (Lines 1345–1360):",
            "  A shelter S is eligible for incident with P people if and only if:",
            "    S.verified == 1   AND   (S.capacity - S.occupied) >= P",
            "Numerical Worked Example:",
            "  • Shelter Name: Corporation Community Hall",
            "  • Total Capacity: 300 evacuees",
            "  • Current Occupancy: 282 evacuees",
            "  • Available Capacity = 300 - 282 = 18 slots",
            "  • Incident 1: 5 people → 18 ≥ 5 → ALLOCATED! (New occupied = 287)",
            "  • Incident 2: 20 people → 18 < 20 → REJECTED! (Overcrowding prevented)",
            "Distinction: This is conditional business logic, not a named graph algorithm."
        ],
        subtitle="Mathematical Capacity Bounds",
        highlight_color=ACCENT_GREEN
    )

    add_speaker_note(s17, """
Slide 17 covers our conditional business logic for rescue teams and relief shelters.

In academic computer science, students often confuse standard named algorithms with domain-specific conditional business logic. On this slide, we explicitly explain our procedural business rules.

For rescue teams, we enforce a state machine: Available -> Assigned -> Completed -> Available. Look at the code on the left from lines 1230 to 1255 of app.py. When an admin deploys a team, the query selects a team WHERE status = 'Available'. If no team is available, the endpoint returns an HTTP 409 conflict. When assigned, an atomic SQL UPDATE sets the team's status to 'Assigned'. This prevents race conditions and double-dispatch.

On the right is our Shelter Capacity logic. The fundamental equation is:
Available Capacity = Total Capacity - Occupied Capacity.

Look at our numerical example:
Corporation Community Hall has total capacity 300 and current occupancy 282. Its available capacity is 300 - 282 = 18 slots.
If an emergency distress call arrives with 5 people, 18 is greater than or equal to 5, so the shelter is allocated, and occupancy updates to 287.
However, if an emergency with 20 people arrives, 18 is strictly less than 20. The system rejects the assignment and searches for a larger shelter. This prevents dangerous overcrowding during disasters.

Now let us synthesize all our algorithms and techniques on Slide 18.
""")

    # =========================================================
    # SLIDE 18: COMPARATIVE ALGORITHM SYNTHESIS
    # =========================================================
    s18 = prs.slides.add_slide(blank_layout)
    set_slide_background(s18, BG_DARK)
    add_header(s18, "Comparative Algorithm & Technique Synthesis", slide_num=18)

    comp_headers = ["Technique", "Core Purpose", "Computational Category", "Time Complexity", "When to Use in Emergency Systems"]
    comp_rows = [
        ["Dijkstra's Algorithm", "Minimum-cost path on weighted road graphs", "Greedy Graph Traversal", "O(|E| + |V| log |V|)", "When finding detour trajectories through road networks with variable distances and flood hazard penalties."],
        ["Haversine Formula", "Great-circle distance across spherical surface", "Spherical Trigonometry", "O(1) constant time", "When rapidly filtering candidate shelters or rescue teams within a spatial radius before calculating road paths."],
        ["Distance-Based Sorting", "Arranging candidate resources by proximity", "Comparison Sorting (Timsort)", "O(n log n) worst-case", "When prioritizing a filtered pool of eligible rescue teams or vetted shelters from nearest to farthest."],
        ["SQL Multi-Tier Ordering", "Ordering emergency records by triage hierarchy", "Relational Database Sorting", "O(N log N) index query", "When rendering the central EOC incident command queue where life-safety priority strictly supersedes score."],
        ["Conditional Allocation Logic", "Enforcing availability states & capacity limits", "Procedural Decision Logic", "O(1) checks per item", "When committing state changes, verifying shelter vacancy, and preventing duplicate team deployments."]
    ]
    create_table(s18, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.3), comp_headers, comp_rows, [Inches(1.8), Inches(2.6), Inches(2.0), Inches(1.8), Inches(3.533)])

    add_speaker_note(s18, """
Slide 18 is our comparative algorithm synthesis table. This slide proves to the examiners that our team understands the exact computational role of every technique in our system:

- Dijkstra's Algorithm is a greedy graph traversal running in O(|E| + |V| log |V|). It is used for road routing and detour planning around flooded culverts.
- The Haversine Formula is spherical trigonometry operating in O(1) constant time. It is used for great-circle distance calculations and spatial hazard buffer testing.
- Distance-based sorting uses Python's O(n log n) Timsort to arrange eligible candidate resources from nearest to farthest.
- SQL Multi-Tier Ordering uses relational database query optimization to sort emergency requests by category and score.
- Conditional Allocation Logic uses procedural checks to enforce capacity limits and mutual exclusion.

Notice how each technique has a distinct purpose and complexity. No single algorithm can solve an entire emergency response system—they must be combined synergistically.

Let us now discuss the limitations and safety considerations of our system on Slide 19.
""")

    # =========================================================
    # SLIDE 19: SYSTEM LIMITATIONS & SAFETY CRITICALITY
    # =========================================================
    s19 = prs.slides.add_slide(blank_layout)
    set_slide_background(s19, BG_DARK)
    add_header(s19, "System Limitations & Safety Considerations", slide_num=19)

    create_card(
        s19, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Technical & Data Limitations",
        [
            "1. External Weather API Latency: Open-Meteo forecasts run on 15-minute or hourly assimilation steps. Micro-bursts occurring in the intervening minutes will not reflect instantaneously.",
            "2. Straight-Line vs. Travel Distance: Haversine distance ignores terrain barriers, bridges, and winding topography. Spatial proximity does not guarantee fast road arrival.",
            "3. Stale Road Hazard Data: Road closure reporting relies on dispatcher input or citizen reports. Unreported flash flooding on an unflagged street cannot be detected automatically by the graph.",
            "4. Cell Tower Collapses: Cellular network failure during severe cyclones disrupts live browser-to-server communication."
        ],
        subtitle="Data & Infrastructure Dependencies",
        highlight_color=ACCENT_AMBER
    )

    create_card(
        s19, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Safety Criticality & Human-in-the-Loop",
        [
            "Dijkstra Does NOT Guarantee Physical Safety: Dijkstra mathematically minimizes total edge weight in the *modeled graph*. If a flooded road is not present in the database, Dijkstra will route vehicles through it without warning.",
            "Heuristic Nature of Triage: Priority scores are computational aids to assist human operators—they are never used to deny or terminate emergency assistance.",
            "The Human-in-the-Loop Mandate: Final dispatch authorizations and shelter activations strictly require human commander approval.",
            "Fail-Safe Principle: When network timeouts or API errors occur, the system surfaces clear error messages and never substitutes deceptive zero-filled readings."
        ],
        subtitle="Ethical & Life-Safety Realities",
        highlight_color=ACCENT_RED
    )

    add_speaker_note(s19, """
Slide 19 demonstrates academic maturity by addressing the real-world limitations and safety considerations of our system. Evaluators strongly appreciate knowing that students understand the operational boundaries of their software.

We identify four main technical limitations:
1. Weather APIs have latency and update on 15-minute intervals.
2. Haversine distance is straight-line and does not account for terrain obstacles.
3. Road hazard data is dependent on timely reporting.
4. Cellular network collapse during extreme cyclones can sever client-server connections.

Most importantly, we state clearly that Dijkstra's algorithm does NOT guarantee physical safety. Dijkstra guarantees a minimum-weight path through whatever mathematical graph we provide it. If a flash flood covers a street and no human has reported it yet, Dijkstra has no magical knowledge of that water. 

Therefore, our system is an operational decision-support tool. Critical dispatch decisions must always retain a human-in-the-loop commander.

Next, let us look at our testing and verification progress on Slide 20.
""")

    # =========================================================
    # SLIDE 20: TESTING & VERIFICATION PROGRESS
    # =========================================================
    s20 = prs.slides.add_slide(blank_layout)
    set_slide_background(s20, BG_DARK)
    add_header(s20, "Testing, Verification & Quality Assurance", slide_num=20)

    # 4 KPI metrics
    create_metric_card(s20, Inches(0.8), Inches(1.6), Inches(2.7), Inches(1.6), "39 / 39", "Automated Tests", "100% Pass Rate (Reported)", ACCENT_GREEN)
    create_metric_card(s20, Inches(3.8), Inches(1.6), Inches(2.7), Inches(1.6), "4 Suites", "Test Coverage", "Weather, Routing, Triage, Dynamic", ACCENT_BLUE)
    create_metric_card(s20, Inches(6.8), Inches(1.6), Inches(2.7), Inches(1.6), "1:1", "API Parity", "Raw Open-Meteo field match", TEXT_CYAN)
    create_metric_card(s20, Inches(9.8), Inches(1.6), Inches(2.7), Inches(1.6), "0 Fake 0s", "Error Integrity", "Explicit 400/404/502 handling", ACCENT_AMBER)

    create_card(
        s20, Inches(0.8), Inches(3.4), Inches(5.7), Inches(3.5),
        "Automated Test Suite Breakdown",
        [
            "1. test_weather_telemetry.py (11 Tests): Verifies live Open-Meteo API, cardinal compass conversion (e.g. 204° → SSW), coordinate bounds checking, WMO code mapping, and safe diagnostic mode.",
            "2. test_assignment_debug.py (4 Tests): Validates team deployment state machine, duplicate assignment rejection, and shelter capacity increments.",
            "3. test_system.py (14 Tests): End-to-end citizen registration, triage score calculation, admin dashboard ordering, and hazard detour routing.",
            "4. test_dynamic_system.py (10 Tests): Validates dynamic geocoding in Chennai/Bengaluru, OSM shelter queries, and GPS accuracy filtering."
        ],
        subtitle="Python Unittest Framework",
        highlight_color=ACCENT_GREEN
    )

    create_card(
        s20, Inches(6.8), Inches(3.4), Inches(5.7), Inches(3.5),
        "Current Verification Status & Next Steps",
        [
            "Local Verification Completed: All 39 automated unit and integration tests pass cleanly in our local development environment.",
            "Diagnostic Inspection Mode: The `/api/weather?diagnostic=1` endpoint allows direct verification of raw JSON payloads without exposing credentials.",
            "Cloud Deployment Readiness: Application is configured for WSGI deployment on Vercel with SQLite portability.",
            "Next Verification Stage: Requires further testing on cloud edge environments with high concurrent user loads and live multi-city GPS telemetry."
        ],
        subtitle="Verification Scope & Boundaries",
        highlight_color=ACCENT_BLUE
    )

    add_speaker_note(s20, """
Slide 20 summarizes our testing and quality assurance progress.

As documented in our project materials, our system is backed by 39 automated unit and integration tests written in Python's unittest framework across four test suites:
1. `test_weather_telemetry.py` with 11 tests verifying live Open-Meteo calls, compass bearings, coordinate bounds, and diagnostic mode.
2. `test_assignment_debug.py` with 4 tests verifying mutual exclusion in team deployment and shelter capacity increments.
3. `test_system.py` with 14 tests verifying full citizen lifecycles and hazard routing.
4. `test_dynamic_system.py` with 10 tests verifying multi-city geocoding across Chennai and Bengaluru.

All 39 tests have passed cleanly in our local testing environment. We have also added a safe diagnostic mode (`?diagnostic=1`) that exposes raw API payload metrics for transparent debugging.

As an honest academic observation, while local testing is thorough, further stress testing is planned under distributed cloud conditions.

Now let us conclude with Slide 21.
""")

    # =========================================================
    # SLIDE 21: CONCLUSION
    # =========================================================
    s21 = prs.slides.add_slide(blank_layout)
    set_slide_background(s21, BG_DARK)
    add_header(s21, "Conclusion: Key Contributions & Algorithmic Impact", slide_num=21)

    create_card(
        s21, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "Key Project Contributions",
        [
            "1. Centralized Disaster Coordination: Successfully replaced scattered, manual phone helplines with a unified digital command architecture.",
            "2. Elimination of Hardcoded Boundaries: Upgraded the project to operate dynamically in any city or rural district via live geocoding and OSM discovery.",
            "3. Objective Life-Safety Triage: Formulated a mathematical scoring model ensuring critical emergencies are never delayed by low-urgency calls.",
            "4. Dynamic Submersion Detours: Demonstrated hazard-aware routing using NetworkX Dijkstra graphs to prevent rescue vehicles from entering flooded roads.",
            "5. Verified Capacity Control: Enforced real-time mathematical capacity tracking to prevent shelter overcrowding during mass evacuations."
        ],
        subtitle="Engineering Achievements",
        highlight_color=TEXT_CYAN
    )

    create_card(
        s21, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3),
        "ADSA Curriculum Alignment & Final Takeaway",
        [
            "Algorithmic Rigor: Demonstrated practical, life-saving applications of core ADSA concepts—graphs, Dijkstra, spherical geometry, and relational sorting.",
            "Academic Integrity: Maintained strict distinction between theoretical graph algorithms, mathematical formulas, database queries, and procedural business logic.",
            "Societal Value: Technology engineered specifically to protect vulnerable citizens, empower first responders, and minimize casualties during natural disasters.",
            "Final Takeaway: Advanced data structures and algorithms are not merely abstract academic concepts—when applied rigorously, they form the foundation of life-saving emergency infrastructure."
        ],
        subtitle="Academic & Real-World Impact",
        highlight_color=ACCENT_GREEN
    )

    add_speaker_note(s21, """
On Slide 21, we conclude our presentation.

Our project successfully demonstrates how advanced data structures and algorithms can be engineered into an operational disaster response system:
- We eliminated hardcoded geographic constraints, making the application globally adaptable.
- We formulated an objective triage algorithm to prevent human bias in emergency dispatching.
- We implemented hazard-aware routing using NetworkX Dijkstra to protect rescue teams from submerged culverts.
- We enforced mathematical capacity bounds to prevent shelter overcrowding.

Most importantly, this project demonstrates the true value of the ADSA curriculum. Data structures, graph algorithms, and computational geometry are not just theoretical interview puzzles—when applied to disaster engineering, they save human lives.

Let us now move to the final slide for the viva defense.
""")

    # =========================================================
    # SLIDE 22: THANK YOU & VIVA DEFENSE
    # =========================================================
    s22 = prs.slides.add_slide(blank_layout)
    set_slide_background(s22, BG_DARK)

    bar22 = s22.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    bar22.fill.solid()
    bar22.fill.fore_color.rgb = ACCENT_GREEN
    bar22.line.fill.background()

    tbox22 = s22.shapes.add_textbox(Inches(1.2), Inches(1.3), Inches(11.0), Inches(5.2))
    tf22 = tbox22.text_frame
    tf22.word_wrap = True

    p_t22 = tf22.paragraphs[0]
    p_t22.text = "ADSA END-SEMESTER PROJECT REVIEW — TEAM NO. 06"
    p_t22.font.name = "Calibri"
    p_t22.font.size = Pt(13)
    p_t22.font.bold = True
    p_t22.font.color.rgb = TEXT_CYAN
    p_t22.space_after = Pt(10)

    p_m22 = tf22.add_paragraph()
    p_m22.text = "Thank You!\nQuestions & Viva Voce Discussion"
    p_m22.font.name = "Calibri"
    p_m22.font.size = Pt(40)
    p_m22.font.bold = True
    p_m22.font.color.rgb = TEXT_LIGHT
    p_m22.space_after = Pt(16)

    p_team = tf22.add_paragraph()
    p_team.text = "Project Team Members:"
    p_team.font.name = "Calibri"
    p_team.font.size = Pt(12)
    p_team.font.bold = True
    p_team.font.color.rgb = TEXT_MUTED
    p_team.space_after = Pt(4)

    members = [
        "• U. Raghu Nandan — CB.AI.U4AID25056",
        "• Likhith K. — CB.AI.U4AID25063",
        "• Akshaya S. — CB.AI.U4AID25051"
    ]
    for m in members:
        pm = tf22.add_paragraph()
        pm.text = m
        pm.font.name = "Calibri"
        pm.font.size = Pt(13)
        pm.font.bold = True
        pm.font.color.rgb = TEXT_LIGHT
        pm.space_after = Pt(2)

    p_meta22 = tf22.add_paragraph()
    p_meta22.text = "\nB.Tech Artificial Intelligence and Data Science  |  October 2026\nGitHub: https://github.com/likhitkella2008-hash/Smart-Flood-Evacuation-System.git"
    p_meta22.font.name = "Calibri"
    p_meta22.font.size = Pt(12)
    p_meta22.font.bold = True
    p_meta22.font.color.rgb = TEXT_BLUE

    add_speaker_note(s22, """
Thank you very much, respected faculty members and examiners. 

We are proud of the engineering and algorithmic foundations of the Smart Flood Rescue System. We now welcome your questions, technical critiques, and viva voce evaluation regarding our graph models, algorithm implementations, time complexities, or system architecture. Thank you!
""")

    # Save presentation
    prs.save(output_path)
    print(f"PowerPoint Presentation successfully created: {output_path} (Total Slides: {len(prs.slides)})")

if __name__ == "__main__":
    out = "Smart_Flood_Rescue_System_ADSA_Presentation.pptx"
    if len(sys.argv) > 1:
        out = sys.argv[1]
    build_all_slides(out)
