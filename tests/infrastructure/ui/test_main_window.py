"""Tests for the main application window."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent

from application.algorithms.registry import build_default_registry
from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from application.use_cases.update_edge import UpdateEdgeUseCase
from application.use_cases.update_node import UpdateNodeUseCase
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)
from infrastructure.serialization.json_project_storage import (
    JsonProjectStorage,
)
from infrastructure.settings import AppSettings
from infrastructure.ui.graph_canvas import ClickEvent, SelectionEvent
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.main_window import APP_NAME, MainWindow


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[AppSettings]:
    """Return AppSettings backed by a temporary file."""
    qsettings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    yield AppSettings(qsettings)
    qsettings.clear()


@pytest.fixture
def window(qtbot: object, settings: AppSettings) -> Iterator[MainWindow]:
    """Return a fully wired MainWindow for testing."""
    repository = InMemoryGraphRepository()
    layout_service = LayoutService()
    registry = build_default_registry()
    storage = JsonProjectStorage()

    widget = MainWindow(
        repository=repository,
        layout_service=layout_service,
        registry=registry,
        storage=storage,
        settings=settings,
        add_node_use_case=AddNodeUseCase(repository),
        add_edge_use_case=AddEdgeUseCase(repository),
        remove_node_use_case=RemoveNodeUseCase(repository),
        remove_edge_use_case=RemoveEdgeUseCase(repository),
        update_edge_use_case=UpdateEdgeUseCase(repository),
        update_node_use_case=UpdateNodeUseCase(repository),
    )
    _ = qtbot
    yield widget
    widget._history.mark_saved()
    widget.close()
    widget.deleteLater()


def _click(
    x: float,
    y: float,
    node_id: int | None = None,
    edge: tuple[int, int] | None = None,
    shift: bool = False,
    double: bool = False,
) -> ClickEvent:
    return ClickEvent(x=x, y=y, node_id=node_id, edge=edge, shift=shift, double=double)


def test_initial_title_is_app_name(window: MainWindow) -> None:
    """A fresh window shows the app name in the title."""
    assert window.windowTitle() == APP_NAME


def test_initial_mode_is_select(window: MainWindow) -> None:
    """The window starts in SELECT mode."""
    assert window.mode is InteractionMode.SELECT


def test_initial_stats_show_zero(window: MainWindow) -> None:
    """The status bar shows zero nodes and zero edges."""
    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_add_node_marks_dirty(window: MainWindow) -> None:
    """Adding a node marks the project as dirty."""
    window._handle_add_node(0.5, 0.5)

    assert window._history.is_dirty() is True


def test_add_node_updates_stats(window: MainWindow) -> None:
    """Adding a node updates the status bar counters."""
    window._handle_add_node(0.5, 0.5)

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"


def test_undo_reverts_add_node(window: MainWindow) -> None:
    """Undo removes the node added by the last edit."""
    window._handle_add_node(0.5, 0.5)
    window._handle_undo()

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_redo_reapplies_add_node(window: MainWindow) -> None:
    """Redo restores the node removed by undo."""
    window._handle_add_node(0.5, 0.5)
    window._handle_undo()
    window._handle_redo()

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"


def test_close_event_accepted_when_clean(window: MainWindow) -> None:
    """Closing a clean project accepts the event without prompting."""
    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()


def test_editing_locked_while_algorithm_loaded(window: MainWindow) -> None:
    """Clicks are ignored while an algorithm is loaded."""
    window._handle_add_node(0.5, 0.5)
    window._handle_add_node(0.6, 0.6)
    window._algorithm_state = window._algorithm_state.PAUSED

    window._handle_canvas_click(_click(0.5, 0.5, node_id=1))

    assert window._drag_node is None


def test_snap_applies_to_add_node(window: MainWindow) -> None:
    """With snap enabled, added nodes land on grid points."""
    window._snap_to_grid = True
    window._handle_add_node(0.532, 0.478)

    pos = window._positions[1]
    assert pos.x == pytest.approx(0.55, abs=1e-9)
    assert pos.y == pytest.approx(0.5, abs=1e-9)


def test_snap_toggle_persists(window: MainWindow, settings: AppSettings) -> None:
    """Toggling snap saves the preference."""
    window._handle_toggle_snap(True)

    assert settings.snap_to_grid() is True


def test_click_selects_single_node(window: MainWindow) -> None:
    """A plain click selects only the clicked node."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)

    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    assert window._selected_nodes == {1}


def test_shift_click_adds_to_selection(window: MainWindow) -> None:
    """Shift-click adds a node to the current selection."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)

    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2, shift=True))

    assert window._selected_nodes == {1, 2}


def test_shift_click_toggles_off(window: MainWindow) -> None:
    """Shift-clicking a selected node removes it from the selection."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1, shift=True))

    assert window._selected_nodes == set()


def test_click_on_empty_clears_selection(window: MainWindow) -> None:
    """Clicking empty space clears the selection."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    window._handle_canvas_click(_click(0.8, 0.8, node_id=None))

    assert window._selected_nodes == set()


def test_rubber_band_selects_nodes_inside(window: MainWindow) -> None:
    """Rubber-band selects every node within the rectangle."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.3, 0.3)
    window._handle_add_node(0.9, 0.9)

    window._handle_selection_complete(
        SelectionEvent(x1=0.0, y1=0.0, x2=0.5, y2=0.5, additive=False)
    )

    assert window._selected_nodes == {1, 2}


def test_rubber_band_additive_keeps_previous(window: MainWindow) -> None:
    """An additive rubber-band selection extends the existing one."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.5, 0.5)
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))

    window._handle_selection_complete(
        SelectionEvent(x1=0.4, y1=0.4, x2=0.6, y2=0.6, additive=True)
    )

    assert window._selected_nodes == {1, 2}


def test_copy_paste_creates_new_node(window: MainWindow) -> None:
    """Copy/paste duplicates a selected node."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_copy()

    window._handle_paste()

    assert window._stats_label.text() == "Nodes: 2   Edges: 0"


def test_copy_paste_preserves_edges(window: MainWindow) -> None:
    """Copy/paste duplicates the edges between selected nodes."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2, weight=2.0)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2, shift=True))
    window._handle_copy()

    window._handle_paste()

    assert window._stats_label.text() == "Nodes: 4   Edges: 2"


def test_paste_does_nothing_without_clipboard(window: MainWindow) -> None:
    """Paste without prior copy does not change the graph."""
    window._handle_paste()

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_delete_selected_removes_all(window: MainWindow) -> None:
    """Delete Selected removes every selected node."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2, shift=True))

    window._handle_delete_selected()

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"
    assert window._selected_nodes == set()


def test_select_all_selects_every_node(window: MainWindow) -> None:
    """Edit → Select All marks every node."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.3, 0.3)

    window._handle_select_all()

    assert window._selected_nodes == {1, 2, 3}


def test_drag_moves_all_selected_nodes(window: MainWindow) -> None:
    """Dragging a selected node moves every selected node together."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2, shift=True))

    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_drag_move(0.3, 0.3)

    assert window._positions[1].x == pytest.approx(0.3, abs=1e-9)
    assert window._positions[2].x == pytest.approx(0.5, abs=1e-9)
    assert window._positions[2].y == pytest.approx(0.5, abs=1e-9)
    window._handle_canvas_drag_end()
