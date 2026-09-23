"""Graphviz DOT for the traceability flow (Yarn Cone -> COBs), rendered by st.graphviz_chart."""
from services.traceability_service import TraceResult
from utils.dates import to_display

CONE_FILL = "#d7e6fb"
COB_FILL = "#f3f6fa"
HIGHLIGHT_FILL = "#ffd54f"


def build_dot(trace: TraceResult, highlight_cob: str | None = None) -> str:
    lines = [
        "digraph trace {",
        "  rankdir=TB;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
    ]
    if trace.cone:
        c = trace.cone
        lines.append(
            f'  cone [label="Yarn Cone: {c.cy_id}\\nAutoconer: {c.autoconer_id}\\nDrum: {c.drum_id}'
            f'\\n{to_display(c.cone_scan_datetime)}", fillcolor="{CONE_FILL}"];'
        )
    for i, cob in enumerate(trace.cobs):
        fill = HIGHLIGHT_FILL if cob.cob_id == highlight_cob else COB_FILL
        lines.append(
            f'  cob{i} [label="{cob.cob_id}\\nSpeedframe: {cob.speedframe_id}\\nSpindle: {cob.spindle_id}'
            f'\\n{to_display(cob.cob_scan_datetime)}", fillcolor="{fill}"];'
        )
        if trace.cone:
            lines.append(f"  cone -> cob{i};")
    lines.append("}")
    return "\n".join(lines)
