"""Tests for the generator dialog."""

from collections.abc import Iterator

import pytest

from application.generators import GeneratorKind
from infrastructure.ui.dialogs.generate_graph_dialog import (
    _ROW_EDGES,
    _ROW_NEIGHBORS,
    _ROW_PROBABILITY,
    _ROW_REWIRING,
    GenerateGraphDialog,
)


@pytest.fixture
def dialog(qtbot: object) -> Iterator[GenerateGraphDialog]:
    """Return a fresh generator dialog."""
    _ = qtbot
    widget = GenerateGraphDialog()
    yield widget
    widget.deleteLater()


def _visible_rows(dialog: GenerateGraphDialog) -> set[int]:
    return {
        index
        for index in range(dialog._form.rowCount())
        if dialog._form.isRowVisible(index)
    }


def test_default_kind_is_erdos_renyi(dialog: GenerateGraphDialog) -> None:
    """Erdős–Rényi is selected by default."""
    assert dialog._kind_combo.currentData() is GeneratorKind.ERDOS_RENYI


def test_default_erdos_renyi_shows_probability_only(
    dialog: GenerateGraphDialog,
) -> None:
    """With ER selected, only the probability row is visible."""
    visible = _visible_rows(dialog)
    assert _ROW_PROBABILITY in visible
    assert _ROW_EDGES not in visible
    assert _ROW_NEIGHBORS not in visible
    assert _ROW_REWIRING not in visible


def test_switching_to_barabasi_shows_edges_row(
    dialog: GenerateGraphDialog,
) -> None:
    """Switching to BA reveals the edges-per-node row."""
    for index in range(dialog._kind_combo.count()):
        if dialog._kind_combo.itemData(index) is GeneratorKind.BARABASI_ALBERT:
            dialog._kind_combo.setCurrentIndex(index)
            break

    visible = _visible_rows(dialog)
    assert _ROW_EDGES in visible
    assert _ROW_PROBABILITY not in visible


def test_switching_to_watts_shows_two_rows(
    dialog: GenerateGraphDialog,
) -> None:
    """Switching to WS reveals both WS rows."""
    for index in range(dialog._kind_combo.count()):
        if dialog._kind_combo.itemData(index) is GeneratorKind.WATTS_STROGATZ:
            dialog._kind_combo.setCurrentIndex(index)
            break

    visible = _visible_rows(dialog)
    assert _ROW_NEIGHBORS in visible
    assert _ROW_REWIRING in visible
    assert _ROW_PROBABILITY not in visible
    assert _ROW_EDGES not in visible


def test_request_reflects_fields(dialog: GenerateGraphDialog) -> None:
    """The request carries the current field values."""
    dialog._node_count_spin.setValue(42)
    dialog._probability_spin.setValue(0.75)

    request = dialog.request()

    assert request.kind is GeneratorKind.ERDOS_RENYI
    assert request.node_count == 42
    assert request.probability == pytest.approx(0.75)


def test_request_uses_selected_kind(dialog: GenerateGraphDialog) -> None:
    """The request reports the currently selected generator."""
    for index in range(dialog._kind_combo.count()):
        if dialog._kind_combo.itemData(index) is GeneratorKind.WATTS_STROGATZ:
            dialog._kind_combo.setCurrentIndex(index)
            break
    dialog._neighbors_spin.setValue(6)
    dialog._rewiring_spin.setValue(0.5)

    request = dialog.request()

    assert request.kind is GeneratorKind.WATTS_STROGATZ
    assert request.neighbors_per_node == 6
    assert request.rewiring_probability == pytest.approx(0.5)
