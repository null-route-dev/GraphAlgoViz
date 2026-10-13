"""Tests for the graph canvas and its geometry helpers."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from domain.entities.edge import Edge
from domain.value_objects.position import Position
from infrastructure.ui.graph_canvas import (
    ARC_SPACING,
    ClickEvent,
    GraphCanvas,
    SelectionEvent,
    _arc_midpoint,
    _arc_rad_for_index,
    _effective_rad,
    _group_edges_by_endpoints,
    _lerp_color,
    _point_to_segment_distance,
    _shorten_towards,
)


@pytest.fixture
def canvas(qtbot: object) -> Iterator[GraphCanvas]:
    """Return a GraphCanvas for export tests."""
    _ = qtbot
    widget = GraphCanvas()
    yield widget
    widget.deleteLater()


def test_lerp_at_zero_returns_start() -> None:
    """At t=0 the start color is returned unchanged."""
    assert _lerp_color("#000000", "#ffffff", 0.0) == "#000000"


def test_lerp_at_one_returns_end() -> None:
    """At t=1 the end color is returned unchanged."""
    assert _lerp_color("#000000", "#ffffff", 1.0) == "#ffffff"


def test_lerp_at_half_returns_midpoint() -> None:
    """At t=0.5 the midpoint between two colors is returned."""
    assert _lerp_color("#000000", "#ffffff", 0.5) == "#808080"


def test_lerp_clamps_below_zero() -> None:
    """Values below 0.0 are treated as 0.0."""
    assert _lerp_color("#000000", "#ffffff", -0.5) == "#000000"


def test_lerp_clamps_above_one() -> None:
    """Values above 1.0 are treated as 1.0."""
    assert _lerp_color("#000000", "#ffffff", 1.5) == "#ffffff"


def test_group_single_edge() -> None:
    """A single edge forms a group of one."""
    edge = Edge(source=1, target=2)
    groups = _group_edges_by_endpoints([edge])

    assert groups == {(1, 2): [edge]}


def test_group_shared_for_both_directions() -> None:
    """Edges in both directions share the same group."""
    forward = Edge(source=1, target=2)
    backward = Edge(source=2, target=1)
    groups = _group_edges_by_endpoints([forward, backward])

    assert len(groups[(1, 2)]) == 2


def test_arc_rad_single_edge_is_zero() -> None:
    """A single edge is not bent."""
    assert _arc_rad_for_index(0, 1) == 0.0


def test_arc_rad_two_edges_symmetric() -> None:
    """Two edges are bent symmetrically around the straight line."""
    first = _arc_rad_for_index(0, 2)
    second = _arc_rad_for_index(1, 2)

    assert first == pytest.approx(-ARC_SPACING / 2)
    assert second == pytest.approx(ARC_SPACING / 2)


def test_effective_rad_keeps_sign_for_canonical_direction() -> None:
    """An edge oriented from the smaller id keeps the slot sign."""
    assert _effective_rad(Edge(source=1, target=2), (1, 2), 0.5) == 0.5


def test_effective_rad_inverts_sign_for_reverse_edge() -> None:
    """An edge oriented from the larger id inverts the slot sign."""
    assert _effective_rad(Edge(source=2, target=1), (1, 2), 0.5) == -0.5


def test_arc_midpoint_straight_line() -> None:
    """A straight edge has its label at the geometric midpoint."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=1.0, y=0.0)

    assert _arc_midpoint(start, end, 0.0) == (0.5, 0.0)


def test_arc_midpoint_positive_rad_shifts_up() -> None:
    """A positive curvature shifts the label above the straight line."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=1.0, y=0.0)

    _, y_up = _arc_midpoint(start, end, 0.5)

    assert y_up > 0.0


def test_arc_midpoint_negative_rad_shifts_down() -> None:
    """A negative curvature shifts the label below the straight line."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=1.0, y=0.0)

    _, y_down = _arc_midpoint(start, end, -0.5)

    assert y_down < 0.0


def test_arc_midpoint_opposite_rads_are_symmetric() -> None:
    """Opposite curvature values produce symmetric label offsets."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=1.0, y=0.0)

    _, y_up = _arc_midpoint(start, end, 0.5)
    _, y_down = _arc_midpoint(start, end, -0.5)

    assert y_up == pytest.approx(-y_down)


def test_point_to_segment_distance_perpendicular() -> None:
    """A point above the middle of a segment measures the offset."""
    distance = _point_to_segment_distance(0.5, 0.3, 0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(0.3)


def test_point_to_segment_distance_clamps_to_endpoint() -> None:
    """A point beyond the segment measures to the nearest endpoint."""
    distance = _point_to_segment_distance(2.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(1.0)


def test_shorten_towards_returns_point_before_end() -> None:
    """The shortened point lies between start and end."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=1.0, y=0.0)

    result = _shorten_towards(start, end, 0.25)

    assert result.x == pytest.approx(0.75)
    assert result.y == pytest.approx(0.0)


def test_shorten_towards_returns_start_when_too_short() -> None:
    """If the segment is shorter than the requested distance, start wins."""
    start = Position(x=0.0, y=0.0)
    end = Position(x=0.1, y=0.0)

    assert _shorten_towards(start, end, 1.0) == start


def test_click_event_fields() -> None:
    """ClickEvent stores every field."""
    event = ClickEvent(x=0.1, y=0.2, node_id=3, edge=None, shift=True, double=False)

    assert event.x == 0.1
    assert event.y == 0.2
    assert event.node_id == 3
    assert event.edge is None
    assert event.shift is True
    assert event.double is False


def test_selection_event_fields() -> None:
    """SelectionEvent stores every field."""
    event = SelectionEvent(x1=0.1, y1=0.2, x2=0.3, y2=0.4, additive=True)

    assert event.x1 == 0.1
    assert event.y1 == 0.2
    assert event.x2 == 0.3
    assert event.y2 == 0.4
    assert event.additive is True


def test_save_figure_png(canvas: GraphCanvas, tmp_path: Path) -> None:
    """Exporting to PNG creates a non-empty file."""
    path = tmp_path / "graph.png"
    canvas.save_figure(path)

    assert path.exists()
    assert path.stat().st_size > 0


def test_save_figure_png_starts_with_png_magic(
    canvas: GraphCanvas, tmp_path: Path
) -> None:
    """The PNG file has the PNG magic bytes at the start."""
    path = tmp_path / "graph.png"
    canvas.save_figure(path)

    with path.open("rb") as f:
        header = f.read(8)

    assert header == b"\x89PNG\r\n\x1a\n"


def test_save_figure_svg(canvas: GraphCanvas, tmp_path: Path) -> None:
    """Exporting to SVG produces an XML document."""
    path = tmp_path / "graph.svg"
    canvas.save_figure(path)

    content = path.read_text(encoding="utf-8")

    assert "<svg" in content


def test_save_figure_pdf(canvas: GraphCanvas, tmp_path: Path) -> None:
    """Exporting to PDF produces a PDF document."""
    path = tmp_path / "graph.pdf"
    canvas.save_figure(path)

    with path.open("rb") as f:
        header = f.read(4)

    assert header == b"%PDF"


def test_save_figure_custom_dpi(canvas: GraphCanvas, tmp_path: Path) -> None:
    """A higher DPI produces a larger PNG file."""
    low_path = tmp_path / "low.png"
    high_path = tmp_path / "high.png"

    canvas.save_figure(low_path, dpi=50)
    canvas.save_figure(high_path, dpi=200)

    assert high_path.stat().st_size > low_path.stat().st_size


def test_save_figure_invalid_extension_raises(
    canvas: GraphCanvas, tmp_path: Path
) -> None:
    """An unsupported extension makes matplotlib raise."""
    path = tmp_path / "graph.xyz"

    with pytest.raises(ValueError):
        canvas.save_figure(path)
