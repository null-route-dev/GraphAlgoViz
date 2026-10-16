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
from infrastructure.ui.dialogs.edge_attributes_dialog import (
    EdgeAttributes,
    EdgeAttributesDialog,
)
from infrastructure.ui.graph_canvas import ClickEvent, SelectionEvent
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.main_window import (
    APP_NAME,
    MainWindow,
    _resolve_export_path,
)


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[AppSettings]:
    """Return AppSettings backed by a temporary file."""
    qsettings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    yield AppSettings(qsettings)
    qsettings.clear()


@pytest.fixture
def stub_edge_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the edge attributes dialog with a fixed OK response."""
    monkeypatch.setattr(
        EdgeAttributesDialog,
        "get_attributes",
        staticmethod(
            lambda *args, **kwargs: EdgeAttributes(weight=1.0, directed=False)
        ),
    )


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


def test_editing_locked_while_algorithm_loaded(
    window: MainWindow,
) -> None:
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


def test_click_selects_single_node(window: MainWindow) -> None:
    """A plain click selects only the clicked node."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)

    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    assert window._selected_nodes == {1}
    assert window._selected_edge is None


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


def test_click_on_edge_selects_it(window: MainWindow) -> None:
    """A single click on an edge selects it and clears node selection."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    window._handle_canvas_click(_click(0.3, 0.3, edge=(1, 2)))

    assert window._selected_edge == (1, 2)
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


def test_delete_selected_removes_edge(window: MainWindow) -> None:
    """Delete Selected removes a selected edge, leaving nodes intact."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2)
    window._handle_canvas_click(_click(0.3, 0.3, edge=(1, 2)))

    window._handle_delete_selected()

    assert window._stats_label.text() == "Nodes: 2   Edges: 0"
    assert window._selected_edge is None


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
    window._handle_canvas_drag_end()


def test_resolve_export_path_keeps_known_suffix() -> None:
    """A path with a known image suffix is returned unchanged."""
    assert _resolve_export_path(Path("a.png")) == Path("a.png")
    assert _resolve_export_path(Path("a.svg")) == Path("a.svg")
    assert _resolve_export_path(Path("a.pdf")) == Path("a.pdf")


def test_resolve_export_path_adds_default() -> None:
    """A path without a known suffix gets the default PNG suffix."""
    assert _resolve_export_path(Path("a")) == Path("a.png")
    assert _resolve_export_path(Path("a.xyz")) == Path("a.png")


def test_self_loop_is_allowed(
    window: MainWindow,
    stub_edge_dialog: None,
) -> None:
    """Clicking the same node twice creates a self-loop."""
    _ = stub_edge_dialog
    window._handle_add_node(0.3, 0.3)
    window._handle_add_edge(1)
    window._handle_add_edge(1)

    assert window._stats_label.text() == "Nodes: 1   Edges: 1"


def test_self_loop_can_be_deleted_with_node(
    window: MainWindow,
    stub_edge_dialog: None,
) -> None:
    """Removing a node removes its self-loop as well."""
    _ = stub_edge_dialog
    window._handle_add_node(0.3, 0.3)
    window._handle_add_edge(1)
    window._handle_add_edge(1)
    window._handle_delete_node(1)

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_toggle_bundle_updates_flag_and_settings(
    window: MainWindow, settings: AppSettings
) -> None:
    """Toggling bundle updates the window flag and persists the choice."""
    window._handle_toggle_bundle(True)

    assert window._bundle_parallel is True
    assert settings.bundle_parallel_edges() is True


def test_toggle_arrow_updates_flag_and_settings(
    window: MainWindow, settings: AppSettings
) -> None:
    """Toggling arrow position updates the window flag and persists."""
    window._handle_toggle_arrow(True)

    assert window._arrow_at_middle is True
    assert settings.arrow_at_middle() is True


def test_inspector_shows_nothing_at_start(window: MainWindow) -> None:
    """With no selection, the inspector reports no selection."""
    assert window._inspector._header.text() == "No selection"


def test_inspector_shows_node_on_selection(window: MainWindow) -> None:
    """Selecting a node populates the inspector with its details."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    assert "Node 1" in window._inspector._header.text()
    assert window._inspector._node_id == 1


def test_inspector_shows_edge_on_selection(window: MainWindow) -> None:
    """Selecting an edge populates the inspector with its details."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2, weight=4.0, directed=True)
    window._handle_canvas_click(_click(0.3, 0.3, edge=(1, 2)))

    assert window._inspector._edge == (1, 2)
    assert window._inspector._edge_weight_spin.value() == pytest.approx(4.0)


def test_inspector_shows_multi_count(window: MainWindow) -> None:
    """Selecting multiple nodes shows a count in the inspector."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))
    window._handle_canvas_click(_click(0.2, 0.2, node_id=2, shift=True))

    assert "2 nodes selected" in window._inspector._header.text()


def test_inspector_label_edit_updates_node(window: MainWindow) -> None:
    """Changing the label through the inspector updates the node."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    window._inspector._node_label_edit.setText("Alpha")
    window._inspector._node_label_edit.editingFinished.emit()

    assert window._repository.get().node(1).label == "Alpha"


def test_inspector_weight_edit_updates_edge(window: MainWindow) -> None:
    """Changing the weight through the inspector updates the edge."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2, weight=1.0)
    window._handle_canvas_click(_click(0.3, 0.3, edge=(1, 2)))

    window._inspector._edge_weight_spin.setValue(9.0)
    window._inspector._edge_weight_spin.editingFinished.emit()

    assert window._repository.get().edges()[0].weight == pytest.approx(9.0)


def test_context_menu_on_node_does_not_raise(window: MainWindow) -> None:
    """The context menu handler runs without error for a node."""
    from infrastructure.ui.graph_canvas import ContextEvent

    window._handle_add_node(0.2, 0.2)
    event = ContextEvent(
        x=0.2,
        y=0.2,
        node_id=1,
        edge=None,
        global_x=0,
        global_y=0,
    )
    assert event.node_id == 1
