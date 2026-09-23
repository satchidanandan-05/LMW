from services.traceability_service import get_traceability
from ui.graph import HIGHLIGHT_FILL, build_dot


def test_dot_has_cone_and_one_edge_per_cob(engine):
    dot = build_dot(get_traceability(engine, "CY", "YC006"))
    assert dot.startswith("digraph")
    assert "Yarn Cone: YC006" in dot and "Autoconer: AC-02" in dot and "Drum: D025" in dot
    assert dot.count("cone -> cob") == 3
    assert HIGHLIGHT_FILL not in dot


def test_dot_highlights_searched_cob(engine):
    dot = build_dot(get_traceability(engine, "COB", "COB005"), highlight_cob="COB005")
    highlighted = [line for line in dot.splitlines() if HIGHLIGHT_FILL in line]
    assert len(highlighted) == 1 and "COB005" in highlighted[0]


def test_dot_for_orphan_cob_has_no_edges(engine):
    dot = build_dot(get_traceability(engine, "COB", "COB099"), highlight_cob="COB099")
    assert "->" not in dot and "COB099" in dot
