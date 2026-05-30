"""Diagram Generator – produces .drawio XML from project intelligence.

Three diagram types, all generated from the built context dict:

  dependency_map   — nodes for each dependency/assumption, edges showing
                     relationships, colour-coded by category.
  risk_heatmap     — risks plotted on a 3×3 impact/likelihood grid.
  scope_overview   — swimlane per intelligence category (risks,
                     assumptions, dependencies, constraints, action items).

No external libraries required – generates raw drawio XML (which is just
a specific flavour of XML that draw.io / diagrams.net can open).

Public API
──────────
    generate(diagram_type, intelligence) -> str (drawio XML)
    DIAGRAM_TYPES -> List[str]
"""

from __future__ import annotations

import html
import textwrap
from typing import Any, Dict, List

DIAGRAM_TYPES = ["dependency_map", "risk_heatmap", "scope_overview"]

# ── Colour palette (matches app dark theme accent colours) ───────────────────
_COLOURS = {
    "risks":       {"fill": "#f8cecc", "stroke": "#b85450"},
    "assumptions": {"fill": "#fff2cc", "stroke": "#d6b656"},
    "dependencies":{"fill": "#dae8fc", "stroke": "#6c8ebf"},
    "constraints": {"fill": "#e1d5e7", "stroke": "#9673a6"},
    "action_items":{"fill": "#d5e8d4", "stroke": "#82b366"},
    "scope":       {"fill": "#f5f5f5", "stroke": "#666666"},
    "default":     {"fill": "#f5f5f5", "stroke": "#666666"},
}

_SEVERITY_COLOURS = {
    "critical": {"fill": "#b85450", "stroke": "#6d1f1c", "font": "#ffffff"},
    "high":     {"fill": "#f8cecc", "stroke": "#b85450", "font": "#000000"},
    "medium":   {"fill": "#fff2cc", "stroke": "#d6b656", "font": "#000000"},
    "low":      {"fill": "#d5e8d4", "stroke": "#82b366", "font": "#000000"},
}


# ── Public entry point ────────────────────────────────────────────────────────

def generate(diagram_type: str, intelligence: Dict[str, Any]) -> str:
    """Generate a drawio XML string for the given diagram type.

    Args:
        diagram_type: One of ``DIAGRAM_TYPES``.
        intelligence: Built context dict from ``build_context()``.

    Returns:
        Complete drawio XML string, ready to save as ``.drawio`` file.

    Raises:
        ValueError: If ``diagram_type`` is not recognised.
    """
    if diagram_type == "dependency_map":
        return _dependency_map(intelligence)
    if diagram_type == "risk_heatmap":
        return _risk_heatmap(intelligence)
    if diagram_type == "scope_overview":
        return _scope_overview(intelligence)
    raise ValueError(
        f"Unknown diagram type: '{diagram_type}'. "
        f"Available: {', '.join(DIAGRAM_TYPES)}"
    )


# ── Diagram 1: Dependency Map ─────────────────────────────────────────────────

def _dependency_map(intel: Dict[str, Any]) -> str:
    """Node graph: dependencies as hub nodes connected to related risks/constraints.

    Layout:
      • Dependencies row  — blue hub nodes
      • Risks row         — red nodes
      • Constraints row   — purple nodes
      • Assumptions row   — yellow nodes
      • Action Items row  — green nodes

    Edges: each dependency node is connected to any risk or constraint whose
    text shares a significant keyword with the dependency text (≥5 chars).
    This builds the component → dependency → impact relationship.
    """
    cells: List[str] = []
    cell_id = 10

    categories = [
        ("dependencies", "🔗 Dependencies"),
        ("risks",        "🔴 Risks"),
        ("constraints",  "⛔ Constraints"),
        ("assumptions",  "💭 Assumptions"),
        ("action_items", "✅ Action Items"),
    ]

    page_w      = 980
    lane_x      = 40
    lane_y      = 50
    node_w      = 220
    node_h      = 50
    node_gap_x  = 24
    node_gap_y  = 14
    nodes_per_row = 3
    header_h    = 36
    padding     = 16

    # First pass: create all swimlane nodes and record node cell IDs per category
    node_ids: Dict[str, List[tuple]] = {}  # cat_key -> [(cell_id, item_text)]

    for cat_key, cat_label in categories:
        raw_items = intel.get(cat_key) or []
        items = [i for i in raw_items if isinstance(i, str) and i.strip()]
        if not items:
            continue

        col = _COLOURS.get(cat_key, _COLOURS["default"])
        rows = (len(items) + nodes_per_row - 1) // nodes_per_row
        lane_h = header_h + padding + rows * (node_h + node_gap_y) + padding

        lane_id = cell_id
        cell_id += 1
        cells.append(
            f'<mxCell id="{lane_id}" value="{_esc(cat_label)}" '
            f'style="swimlane;startSize={header_h};fillColor={col["fill"]};'
            f'strokeColor={col["stroke"]};fontSize=13;fontStyle=1;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{lane_x}" y="{lane_y}" '
            f'width="{page_w - lane_x * 2}" height="{lane_h}" as="geometry" />'
            f'</mxCell>'
        )

        cat_nodes: List[tuple] = []
        for idx, item in enumerate(items[:12]):
            row = idx // nodes_per_row
            col_idx = idx % nodes_per_row
            nx = padding + col_idx * (node_w + node_gap_x)
            ny = header_h + padding + row * (node_h + node_gap_y)
            label = _wrap(item, 32)
            nid = cell_id
            cells.append(
                f'<mxCell id="{nid}" value="{_esc(label)}" '
                f'style="rounded=1;whiteSpace=wrap;html=1;fontSize=10;'
                f'fillColor={col["fill"]};strokeColor={col["stroke"]};" '
                f'vertex="1" parent="{lane_id}">'
                f'<mxGeometry x="{nx}" y="{ny}" '
                f'width="{node_w}" height="{node_h}" as="geometry" />'
                f'</mxCell>'
            )
            cat_nodes.append((nid, item))
            cell_id += 1

        node_ids[cat_key] = cat_nodes
        lane_y += lane_h + 20

    # Second pass: draw edges from each dependency to related risks/constraints.
    # "Related" = at least one significant keyword (≥5 chars) is shared.
    dep_nodes   = node_ids.get("dependencies", [])
    risk_nodes  = node_ids.get("risks", [])
    const_nodes = node_ids.get("constraints", [])

    def _keywords(text: str) -> set:
        return {w.lower() for w in text.split() if len(w) >= 5}

    for dep_id, dep_text in dep_nodes:
        dep_kw = _keywords(dep_text)
        related = [
            (nid, txt) for nid, txt in (risk_nodes + const_nodes)
            if dep_kw & _keywords(txt)
        ]
        for rel_id, _ in related[:3]:  # cap at 3 edges per dependency node
            cells.append(
                f'<mxCell id="{cell_id}" style="edgeStyle=orthogonalEdgeStyle;'
                f'rounded=1;orthogonalLoop=1;jettySize=auto;exitX=0.5;exitY=1;'
                f'entryX=0.5;entryY=0;fontSize=9;strokeColor=#6c8ebf;'
                f'strokeWidth=1;dashed=1;" '
                f'edge="1" source="{dep_id}" target="{rel_id}" parent="1">'
                f'<mxGeometry relative="1" as="geometry" />'
                f'</mxCell>'
            )
            cell_id += 1

    # Review context label
    rc = intel.get("_review_context")
    if rc:
        ctx_label = f"Review: {rc.get('review_id','')} · {rc.get('persona','')}"
        cells.append(
            f'<mxCell id="{cell_id}" value="{_esc(ctx_label)}" '
            f'style="text;html=1;align=left;fontSize=10;fontColor=#6c8ebf;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{lane_x}" y="16" width="600" height="20" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    title = _project_title(intel)
    return _wrap_mxfile(
        diagram_id="dependency-map",
        diagram_name="Dependency Map",
        title=title,
        cells=cells,
        page_w=page_w,
        page_h=lane_y + 40,
    )


# ── Diagram 2: Risk Heatmap ───────────────────────────────────────────────────

def _risk_heatmap(intel: Dict[str, Any]) -> str:
    """3×3 grid: Impact (Low/Med/High) vs Likelihood (Low/Med/High)."""
    cells: List[str] = []

    # Grid layout
    cell_w, cell_h = 260, 200
    origin_x, origin_y = 120, 80  # after axis labels
    axis_label_w = 110
    axis_label_h = 40

    # Grid colours (traffic-light: green=low, amber=med, red=high)
    grid_colours = [
        # row 0 (High likelihood), row 1 (Med), row 2 (Low)
        ["#fff2cc", "#f8cecc", "#f8cecc"],   # High likelihood
        ["#d5e8d4", "#fff2cc", "#f8cecc"],   # Med likelihood
        ["#d5e8d4", "#d5e8d4", "#fff2cc"],   # Low likelihood
    ]
    grid_strokes = [
        ["#d6b656", "#b85450", "#b85450"],
        ["#82b366", "#d6b656", "#b85450"],
        ["#82b366", "#82b366", "#d6b656"],
    ]

    likelihood_labels = ["High", "Medium", "Low"]
    impact_labels     = ["Low", "Medium", "High"]

    cell_id = 10

    # Draw grid cells
    for r in range(3):
        for c in range(3):
            gx = origin_x + c * cell_w
            gy = origin_y + r * cell_h
            cells.append(
                f'<mxCell id="{cell_id}" value="" '
                f'style="rounded=0;fillColor={grid_colours[r][c]};'
                f'strokeColor={grid_strokes[r][c]};opacity=60;" '
                f'vertex="1" parent="1">'
                f'<mxGeometry x="{gx}" y="{gy}" '
                f'width="{cell_w}" height="{cell_h}" as="geometry" />'
                f'</mxCell>'
            )
            cell_id += 1

    # Y-axis label (Likelihood)
    cells.append(
        f'<mxCell id="{cell_id}" value="&lt;b&gt;Likelihood&lt;/b&gt;" '
        f'style="text;html=1;align=center;rotation=-90;fontSize=13;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="10" y="{origin_y + cell_h}" '
        f'width="100" height="30" as="geometry" />'
        f'</mxCell>'
    )
    cell_id += 1

    # X-axis label (Impact)
    cells.append(
        f'<mxCell id="{cell_id}" value="&lt;b&gt;Impact&lt;/b&gt;" '
        f'style="text;html=1;align=center;fontSize=13;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{origin_x + cell_w}" y="{origin_y + 3*cell_h + 10}" '
        f'width="100" height="30" as="geometry" />'
        f'</mxCell>'
    )
    cell_id += 1

    # Row/col axis tick labels
    for r, lbl in enumerate(likelihood_labels):
        cells.append(
            f'<mxCell id="{cell_id}" value="{lbl}" '
            f'style="text;html=1;align=right;fontSize=11;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{origin_x - axis_label_w}" '
            f'y="{origin_y + r*cell_h + cell_h//2 - 12}" '
            f'width="{axis_label_w - 8}" height="24" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1
    for c, lbl in enumerate(impact_labels):
        cells.append(
            f'<mxCell id="{cell_id}" value="{lbl}" '
            f'style="text;html=1;align=center;fontSize=11;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{origin_x + c*cell_w}" '
            f'y="{origin_y + 3*cell_h + 6}" '
            f'width="{cell_w}" height="24" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    # Place risks on the grid.
    # Collect all risks; include non-string items from review findings dicts.
    raw_risks = intel.get("risks") or []
    risks: List[str] = []
    for r in raw_risks:
        if isinstance(r, str) and r.strip():
            risks.append(r.strip())
        elif isinstance(r, dict):
            t = r.get("description") or r.get("risk") or r.get("text") or ""
            if t.strip():
                risks.append(t.strip())

    # Track slots used per cell: (row, col) -> count
    slot_count: Dict[tuple, int] = {}
    MAX_SLOTS = 4   # max chips per grid cell before wrapping to next cell
    MAX_RISKS = 36  # total cap

    for risk in risks[:MAX_RISKS]:
        r_idx, c_idx = _classify_risk(risk)

        # Find the first cell (scanning row-by-row) that still has space.
        # This ensures overflow risks are distributed instead of silently dropped.
        placed = False
        for attempt in range(9):  # 9 cells in the 3×3 grid
            candidate = ((r_idx + attempt // 3) % 3, (c_idx + attempt % 3) % 3)
            slot = slot_count.get(candidate, 0)
            if slot < MAX_SLOTS:
                r_idx, c_idx = candidate
                slot_count[candidate] = slot + 1
                placed = True
                break
        if not placed:
            continue

        slot = slot_count[(r_idx, c_idx)] - 1  # slot index for y-offset
        gx = origin_x + c_idx * cell_w + 8
        gy = origin_y + r_idx * cell_h + 8 + slot * 46

        sev = _severity_from_risk(risk)
        sc = _SEVERITY_COLOURS[sev]
        label = _wrap(risk, 28)
        cells.append(
            f'<mxCell id="{cell_id}" value="{_esc(label)}" '
            f'style="rounded=1;whiteSpace=wrap;html=1;fontSize=9;'
            f'fillColor={sc["fill"]};strokeColor={sc["stroke"]};'
            f'fontColor={sc["font"]};" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{gx}" y="{gy}" '
            f'width="{cell_w - 16}" height="40" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    # Show risk count in title area
    if risks:
        cells.append(
            f'<mxCell id="{cell_id}" '
            f'value="{len(risks)} risk(s) plotted" '
            f'style="text;html=1;align=left;fontSize=10;fontColor=#666666;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{origin_x}" y="{origin_y + 3*cell_h + 36}" '
            f'width="300" height="20" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    # Review context label
    rc = intel.get("_review_context")
    if rc:
        ctx_label = f"Review: {rc.get('review_id','')} · {rc.get('persona','')}"
        cells.append(
            f'<mxCell id="{cell_id}" value="{_esc(ctx_label)}" '
            f'style="text;html=1;align=left;fontSize=10;fontColor=#6c8ebf;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{origin_x}" y="10" width="600" height="20" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    title = _project_title(intel)
    return _wrap_mxfile(
        diagram_id="risk-heatmap",
        diagram_name="Risk Heatmap",
        title=title,
        cells=cells,
        page_w=origin_x + 3 * cell_w + 60,
        page_h=origin_y + 3 * cell_h + 80,
    )


# ── Diagram 3: Scope Overview ─────────────────────────────────────────────────

def _scope_overview(intel: Dict[str, Any]) -> str:
    """Summary swimlane: one lane per category showing item count + list."""
    cells: List[str] = []
    cell_id = 10

    categories = [
        ("scope",        "📄 Scope",        "scope"),
        ("risks",        "🔴 Risks",        "risks"),
        ("assumptions",  "💭 Assumptions",  "assumptions"),
        ("dependencies", "🔗 Dependencies", "dependencies"),
        ("constraints",  "⛔ Constraints",  "constraints"),
        ("action_items", "✅ Action Items", "action_items"),
    ]

    page_w   = 800
    lane_x   = 40
    lane_y   = 50
    header_h = 36
    item_h   = 22
    padding  = 12
    min_h    = 80

    # Review context label above lanes
    rc = intel.get("_review_context")
    if rc:
        ctx_label = f"Review: {rc.get('review_id','')} · {rc.get('persona','')}"
        cells.append(
            f'<mxCell id="{cell_id}" value="{_esc(ctx_label)}" '
            f'style="text;html=1;align=left;fontSize=10;fontColor=#6c8ebf;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{lane_x}" y="16" width="600" height="20" as="geometry" />'
            f'</mxCell>'
        )
        cell_id += 1

    for cat_key, cat_label, _ in categories:
        if cat_key == "scope":
            items = _extract_scope_lines(intel)
        else:
            raw = intel.get(cat_key) or []
            items = []
            for i in raw:
                if isinstance(i, str) and i.strip():
                    items.append(i.strip())
                elif isinstance(i, dict):
                    t = i.get("description") or i.get("text") or i.get("risk") or ""
                    if t.strip():
                        items.append(t.strip())

        col     = _COLOURS.get(cat_key, _COLOURS["default"])
        lane_h  = max(min_h, header_h + padding + len(items) * item_h + padding)
        badge   = f" ({len(items)})" if items else " (none)"

        cells.append(
            f'<mxCell id="{cell_id}" value="{_esc(cat_label + badge)}" '
            f'style="swimlane;startSize={header_h};fillColor={col["fill"]};'
            f'strokeColor={col["stroke"]};fontSize=13;fontStyle=1;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{lane_x}" y="{lane_y}" '
            f'width="{page_w - lane_x*2}" height="{lane_h}" as="geometry" />'
            f'</mxCell>'
        )
        lane_id = cell_id
        cell_id += 1

        for idx, item in enumerate(items[:20]):
            ix = padding
            iy = header_h + padding + idx * item_h
            cells.append(
                f'<mxCell id="{cell_id}" value="{_esc("• " + item)}" '
                f'style="text;html=1;align=left;fontSize=11;whiteSpace=wrap;" '
                f'vertex="1" parent="{lane_id}">'
                f'<mxGeometry x="{ix}" y="{iy}" '
                f'width="{page_w - lane_x*2 - padding*2}" height="{item_h}" '
                f'as="geometry" />'
                f'</mxCell>'
            )
            cell_id += 1

        if not items:
            cells.append(
                f'<mxCell id="{cell_id}" value="(no items extracted)" '
                f'style="text;html=1;align=left;fontSize=11;'
                f'fontColor=#999999;fontStyle=2;" '
                f'vertex="1" parent="{lane_id}">'
                f'<mxGeometry x="{padding}" y="{header_h + padding}" '
                f'width="400" height="{item_h}" as="geometry" />'
                f'</mxCell>'
            )
            cell_id += 1

        lane_y += lane_h + 16

    title = _project_title(intel)
    return _wrap_mxfile(
        diagram_id="scope-overview",
        diagram_name="Scope Overview",
        title=title,
        cells=cells,
        page_w=page_w,
        page_h=lane_y + 40,
    )


def _extract_scope_lines(intel: Dict[str, Any]) -> List[str]:
    """Extract meaningful lines from the scope field.

    The scope field may be:
      - Plain text paragraphs
      - Multi-fragment blocks separated by "---" (from context_builder)
      - Empty

    Returns up to 12 non-empty lines/sentences suitable for diagram display.
    """
    raw = (intel.get("scope") or "").strip()
    if not raw:
        return []

    # Split on the context_builder separator first
    fragments = [f.strip() for f in raw.split("\n\n---\n\n") if f.strip()]

    lines: List[str] = []
    for fragment in fragments:
        # Each fragment may look like "[source] heading: content..."
        # Strip source prefix if present
        cleaned = fragment
        if cleaned.startswith("[") and "]" in cleaned:
            cleaned = cleaned[cleaned.index("]") + 1:].strip()
        # Further split on newlines
        for line in cleaned.splitlines():
            line = line.strip()
            if line and len(line) > 10:
                lines.append(line[:120])  # cap per-line length for display

    # Fallback: if no structured lines, wrap the raw text
    if not lines and raw:
        lines = [raw[i:i + 100] for i in range(0, min(len(raw), 800), 100)]

    return lines[:12]


# ── Shared helpers ────────────────────────────────────────────────────────────

def _wrap_mxfile(
    diagram_id: str,
    diagram_name: str,
    title: str,
    cells: List[str],
    page_w: int,
    page_h: int,
) -> str:
    title_cell = (
        f'<mxCell id="2" value="{_esc(title)}" '
        f'style="text;html=1;align=center;fontSize=16;fontStyle=1;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="40" y="10" width="{max(page_w - 80, 400)}" '
        f'height="30" as="geometry" />'
        f'</mxCell>'
    )
    all_cells = "\n    ".join([
        '<mxCell id="0" />',
        '<mxCell id="1" parent="0" />',
        title_cell,
    ] + cells)

    return textwrap.dedent(f"""\
        <mxfile host="Project Delivery Accelerator Engine" modified="" agent="Contexta" version="24.0">
          <diagram id="{diagram_id}" name="{_esc(diagram_name)}">
            <mxGraphModel dx="1600" dy="1200" grid="1" gridSize="10" guides="1"
              tooltips="1" connect="1" arrows="1" fold="1" page="0"
              pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}"
              math="0" shadow="0">
              <root>
                {all_cells}
              </root>
            </mxGraphModel>
          </diagram>
        </mxfile>
    """).lstrip()


def _esc(text: str) -> str:
    """HTML-escape for use in XML attribute values."""
    return html.escape(str(text), quote=True)


def _wrap(text: str, width: int = 40) -> str:
    """Wrap text at word boundaries; join with HTML line break."""
    lines = textwrap.wrap(str(text), width=width)
    return "&#xa;".join(lines) if lines else text


def _project_title(intel: Dict[str, Any]) -> str:
    """Extract a short title from intelligence scope or summary."""
    scope = intel.get("scope", "")
    if scope:
        first_line = scope.split("\n")[0].strip()
        return first_line[:80] if first_line else "Project Intelligence Diagram"
    summary = intel.get("summary", "")
    if summary:
        return summary[:80]
    return "Project Intelligence Diagram"


def _classify_risk(risk_text: str) -> tuple:
    """Return (row, col) for the 3×3 heatmap grid.

    row: 0=High likelihood, 1=Med, 2=Low
    col: 0=Low impact, 1=Med, 2=High impact

    Uses broader keyword sets so risks distribute across the grid rather
    than all landing in the same default cell.
    """
    lower = risk_text.lower()

    # ── Impact (column) ────────────────────────────────────────
    if any(k in lower for k in (
        "critical", "catastrophic", "severe", "major", "showstopper",
        "breach", "failure", "loss", "outage", "regulatory", "legal",
        "data", "security", "compliance",
    )):
        col = 2
    elif any(k in lower for k in (
        "significant", "substantial", "considerable", "high impact",
        "delay", "cost", "budget", "resource", "performance", "integration",
        "dependency", "third party", "vendor",
    )):
        col = 1
    else:
        col = 0

    # ── Likelihood (row) ──────────────────────────────────────
    if any(k in lower for k in (
        "likely", "probable", "imminent", "certain", "inevitable", "will",
        "identified", "known", "confirmed", "existing",
    )):
        row = 0
    elif any(k in lower for k in (
        "possible", "may", "could", "moderate", "potential", "risk",
        "if ", "when ", "should", "might",
    )):
        row = 1
    else:
        row = 2

    return row, col


def _severity_from_risk(risk_text: str) -> str:
    """Classify risk severity for heatmap chip colour."""
    lower = risk_text.lower()
    if any(k in lower for k in ("critical", "catastrophic", "showstopper", "breach")):
        return "critical"
    if any(k in lower for k in ("high", "severe", "major", "significant")):
        return "high"
    if any(k in lower for k in ("medium", "moderate", "possible")):
        return "medium"
    return "low"
