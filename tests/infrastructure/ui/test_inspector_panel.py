"""Tests for the inspector panel."""

from collections.abc import Iterator

import pytest

from infrastructure.ui.inspector_panel import InspectorPanel


@pytest.fixture
def panel(qtbot: object) -> Iterator[InspectorPanel]:
    """Return a fresh inspector panel."""
    _ = qtbot
    widget = InspectorPanel()
    yield widget
    widget.deleteLater()


def test_initial_state_shows_no_selection(panel: InspectorPanel) -> None:
    """A fresh inspector reports no selection."""
    assert panel._header.text() == "No selection"
    assert panel._form.rowCount() == 0


def test_show_node_populates_form(panel: InspectorPanel) -> None:
    """show_node puts the label and degree fields into the form."""
    panel.show_node(node_id=3, label="Alpha", degree=4)

    assert panel._header.text() == "Node 3"
    assert panel._node_label_edit.text() == "Alpha"
    assert panel._node_degree_label.text() == "4"
    assert panel._form.rowCount() == 3


def test_show_node_stores_node_id(panel: InspectorPanel) -> None:
    """After show_node, the panel remembers the node id."""
    panel.show_node(node_id=7, label="", degree=0)

    assert panel._node_id == 7


def test_show_edge_populates_form(panel: InspectorPanel) -> None:
    """show_edge puts the weight and directed fields into the form."""
    panel.show_edge(source=1, target=2, weight=3.5, directed=True)

    assert "1" in panel._header.text()
    assert "2" in panel._header.text()
    assert panel._edge_weight_spin.value() == pytest.approx(3.5)
    assert panel._edge_directed_check.isChecked() is True
    assert panel._form.rowCount() == 3


def test_show_edge_stores_endpoints(panel: InspectorPanel) -> None:
    """After show_edge, the panel remembers the endpoints."""
    panel.show_edge(source=1, target=2, weight=1.0, directed=False)

    assert panel._edge == (1, 2)


def test_show_multi_shows_count(panel: InspectorPanel) -> None:
    """show_multi shows the number of selected nodes."""
    panel.show_multi(5)

    assert "5 nodes selected" in panel._header.text()
    assert panel._form.rowCount() == 0


def test_show_nothing_clears(panel: InspectorPanel) -> None:
    """show_nothing resets the panel to the empty state."""
    panel.show_node(node_id=1, label="A", degree=2)

    panel.show_nothing()

    assert panel._header.text() == "No selection"
    assert panel._form.rowCount() == 0


def test_node_label_edit_emits_signal(panel: InspectorPanel) -> None:
    """Editing the label field emits node_label_changed."""
    panel.show_node(node_id=4, label="Old", degree=0)
    received: list[tuple[int, str]] = []
    panel.node_label_changed.connect(lambda nid, label: received.append((nid, label)))

    panel._node_label_edit.setText("New")
    panel._node_label_edit.editingFinished.emit()

    assert received == [(4, "New")]


def test_edge_weight_edit_emits_signal(panel: InspectorPanel) -> None:
    """Editing the weight field emits edge_weight_changed."""
    panel.show_edge(source=1, target=2, weight=1.0, directed=False)
    received: list[tuple[int, int, float]] = []
    panel.edge_weight_changed.connect(lambda s, t, w: received.append((s, t, w)))

    panel._edge_weight_spin.setValue(7.5)
    panel._edge_weight_spin.editingFinished.emit()

    assert len(received) == 1
    assert received[0][0] == 1
    assert received[0][1] == 2
    assert received[0][2] == pytest.approx(7.5)


def test_edge_directed_toggle_emits_signal(panel: InspectorPanel) -> None:
    """Toggling the directed checkbox emits edge_directed_changed."""
    panel.show_edge(source=1, target=2, weight=1.0, directed=False)
    received: list[tuple[int, int, bool]] = []
    panel.edge_directed_changed.connect(lambda s, t, d: received.append((s, t, d)))

    panel._edge_directed_check.setChecked(True)

    assert received == [(1, 2, True)]


def test_show_edge_does_not_emit_during_setup(panel: InspectorPanel) -> None:
    """Setting fields via show_edge does not fire any signals."""
    received: list[tuple[int, int, bool]] = []
    panel.edge_directed_changed.connect(lambda s, t, d: received.append((s, t, d)))

    panel.show_edge(source=1, target=2, weight=1.0, directed=True)

    assert received == []


def test_show_node_does_not_emit_during_setup(panel: InspectorPanel) -> None:
    """Setting the label via show_node does not fire any signals."""
    received: list[tuple[int, str]] = []
    panel.node_label_changed.connect(lambda nid, label: received.append((nid, label)))

    panel.show_node(node_id=1, label="New", degree=0)

    assert received == []
