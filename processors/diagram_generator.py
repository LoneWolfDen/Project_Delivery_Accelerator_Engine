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
    """Nodes for each intelligence item, grouped by category in swimlanes."""
    cells: List[str] = []
    cell_id = 10  # start above reserved 0/1

    categories = [
        ("dependencies", "🔗 Dependencies"),
        ("risks",        "🔴 Risks"),
        ("constraints",  "⛔ Constraints"),
        ("assumptions",  "💭 Assumptions"),
        ("action_items", "✅ Action Items"),
    ]

    lane_width  = 900
    lane_x      = 40
    lane_y      = 40
    node_w      = 220
    node_h      = 50
    node_gap_x  = 20
    node_gap_y  = 14
    nodes_per_row = 3
    header_h    = 36
    padding     = 16

    for cat_key, cat_label in categories:
        items = [i for i in intel.get(cat_key, []) if isinstance(i, str) and i.strip()]
        if not items:
            continue

        col = _COLOURS.get(cat_key, _COLOURS["default"])
        rows = (len(items) + nodes_per_row - 1) // nodes_per_row
        lane_h = header_h + padding + rows * (node_h + node_gap_y) + padding

        # Swimlane container
        lane_id = cell_id
        cell_id += 1
        cells.append(
            f'<mxCell id="{lane_id}" value="{_esc(cat_label)}" '
            f'style="swimlane;startSize={header_h};fillColor={col["fill"]};'
            f'strokeColor={col["stroke"]};fontSize=13;fontStyle=1;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{lane_x}" y="{lane_y}" '
            f'width="{lane_width}" height="{lane_h}" as="geometry" />'
            f'</mxCell>'
        )

        for idx, item in enumerate(items[:12]):  # cap at 12 per category
            row = idx // nodes_per_row
            col_idx = idx % nodes_per_row
            nx = padding + col_idx * (node_w + node_gap_x)
            ny = header_h + padding + row * (node_h + node_gap_y)
            label = _wrap(item, 32)

            cells.append(
                f'<mxCell id="{cell_id}" value="{_esc(label)}" '
                f'style="rounded=1;whiteSpace=wrap;html=1;fontSize=10;'
                f'fillColor={col["fill"]};strokeColor={col["stroke"]};" '
                f'vertex="1" parent="{lane_id}">'
                f'<mxGeometry x="{nx}" y="{ny}" '
                f'width="{node_w}" height="{node_h}" as="geometry" />'
                f'</mxCell>'
            )
            cell_id += 1

        lane_y += lane_h + 20

    title = _project_title(intel)
    return _wrap_mxfile(
        diagram_id="dependency-map",
        diagram_name="Dependency Map",
        title=title,
        cells=cells,
        page_w=lane_width + 80,
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

    # Place risks on the grid
    risks = [r for r in intel.get("risks", []) if isinstance(r, str) and r.strip()]
    # Track slots used per cell: (row, col) -> count
    slot_count: Dict[tuple, int] = {}

    for risk in risks[:18]:  # max 18 risks on the heatmap
        r_idx, c_idx = _classify_risk(risk)
        slot = slot_count.get((r_idx, c_idx), 0)
        slot_count[(r_idx, c_idx)] = slot + 1

        gx = origin_x + c_idx * cell_w + 8
        gy = origin_y + r_idx * cell_h + 8 + slot * 46
        if slot >= 3:  # max 4 per cell; skip overflow
            continue

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
    lane_y   = 40
    header_h = 36
    item_h   = 22
    padding  = 12
    min_h    = 80

    for cat_key, cat_label, _ in categories:
        if cat_key == "scope":
            raw = intel.get("scope", "")
            items = [s.strip() for s in raw.split("\n") if s.strip()][:8] if raw else []
            if not items and raw:
                items = [_wrap(raw, 100)]
        else:
            items = [i for i in intel.get(cat_key, []) if isinstance(i, str) and i.strip()]

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


def _classify_risk(risk_text: str) -> tuple[int, int]:
    """Return (row, col) for the 3×3 heatmap grid.

    row: 0=High likelihood, 1=Med, 2=Low
    col: 0=Low impact, 1=Med, 2=High impact
    """
    lower = risk_text.lower()
    # Impact classification
    if any(k in lower for k in ("critical", "catastrophic", "severe", "major", "showstopper", "breach", "failure")):
        col = 2
    elif any(k in lower for k in ("significant", "substantial", "considerable", "high impact")):
        col = 1
    else:
        col = 0

    # Likelihood classification
    if any(k in lower for k in ("likely", "probable", "imminent", "certain", "inevitable", "will")):
        row = 0
    elif any(k in lower for k in ("possible", "may", "could", "moderate")):
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
