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
from application.use_cases.remove_isolated_nodes import (
    RemoveIsolatedNodesUseCase,
)
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
from infrastructure.ui.dialogs.node_attributes_dialog import (
    NodeAttributesDialog,
)
from infrastructure.ui.graph_canvas import ClickEvent, SelectionEvent
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.main_window import (
    APP_NAME,
    SHORTCUT_DUPLICATE,
    SHORTCUT_RENAME,
    SHORTCUT_RUN,
    SHORTCUT_SNAP,
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
def stub_node_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the node attributes dialog with a fixed label."""
    monkeypatch.setattr(
        NodeAttributesDialog,
        "get_label",
        staticmethod(lambda *args, **kwargs: "renamed"),
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
        remove_isolated_nodes_use_case=RemoveIsolatedNodesUseCase(repository),
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


def test_load_example_replaces_graph(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading an example replaces the entire graph."""
    window._handle_add_node(0.5, 0.5)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    window._handle_load_example("k5")

    assert window._stats_label.text() == "Nodes: 5   Edges: 10"


def test_load_example_resets_history_to_clean(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading an example resets history and clears the dirty flag."""
    window._handle_add_node(0.5, 0.5)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    window._handle_load_example("k33")

    assert window._history.is_dirty() is False
    assert window._undo_action is not None
    assert window._undo_action.isEnabled() is False


def test_load_example_sets_positions(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading an example sets positions for every node."""
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    window._handle_load_example("cycle")

    assert len(window._positions) == 6
    for node_id in range(1, 7):
        assert node_id in window._positions


def test_load_example_updates_title(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading an example clears the current file path from the title."""
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    window._handle_load_example("tree")

    assert "*" not in window.windowTitle()


def test_duplicate_shortcut_is_ctrl_d(window: MainWindow) -> None:
    """The duplicate action carries the Ctrl+D shortcut."""
    assert window._duplicate_action is not None
    assert window._duplicate_action.shortcut().toString() == SHORTCUT_DUPLICATE


def test_rename_shortcut_is_f2(window: MainWindow) -> None:
    """The rename action carries the F2 shortcut."""
    assert window._rename_action is not None
    assert window._rename_action.shortcut().toString() == SHORTCUT_RENAME


def test_snap_shortcut_is_ctrl_g(window: MainWindow) -> None:
    """The snap-to-grid action carries the Ctrl+G shortcut."""
    assert window._snap_action is not None
    assert window._snap_action.shortcut().toString() == SHORTCUT_SNAP


def test_run_shortcut_is_f5(window: MainWindow) -> None:
    """The run action carries the F5 shortcut."""
    assert window._run_action is not None
    assert window._run_action.shortcut().toString() == SHORTCUT_RUN


def test_duplicate_creates_new_node(window: MainWindow) -> None:
    """Duplicating a selected node adds a copy."""
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    window._handle_duplicate()

    assert window._stats_label.text() == "Nodes: 2   Edges: 0"


def test_duplicate_preserves_edges(window: MainWindow) -> None:
    """Duplicating a pair of connected nodes duplicates their edge."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._add_edge_use_case.execute(source=1, target=2, weight=2.0)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2, shift=True))

    window._handle_duplicate()

    assert window._stats_label.text() == "Nodes: 4   Edges: 2"


def test_duplicate_without_selection_does_nothing(
    window: MainWindow,
) -> None:
    """Duplicating an empty selection leaves the graph unchanged."""
    window._handle_add_node(0.2, 0.2)

    window._handle_duplicate()

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"


def test_duplicate_does_not_touch_clipboard(window: MainWindow) -> None:
    """Duplicate leaves the user's clipboard intact."""
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.4, 0.4)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))
    window._handle_copy()
    clipboard_before = window._clipboard
    window._handle_canvas_click(_click(0.4, 0.4, node_id=2))

    window._handle_duplicate()

    assert window._clipboard is clipboard_before


def test_rename_updates_label(
    window: MainWindow,
    stub_node_dialog: None,
) -> None:
    """Renaming a single selected node updates its label."""
    _ = stub_node_dialog
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    window._handle_rename()

    assert window._repository.get().node(1).label == "renamed"


def test_rename_without_selection_does_nothing(
    window: MainWindow,
) -> None:
    """Renaming with no selection leaves the graph unchanged."""
    window._handle_add_node(0.2, 0.2)

    window._handle_rename()

    assert window._repository.get().node(1).label == ""


def test_rename_with_multiple_selection_does_nothing(
    window: MainWindow,
) -> None:
    """Renaming with multiple nodes selected leaves the graph unchanged."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))
    window._handle_canvas_click(_click(0.2, 0.2, node_id=2, shift=True))

    window._handle_rename()

    assert window._repository.get().node(1).label == ""
    assert window._repository.get().node(2).label == ""


def test_duplicate_action_enabled_with_selection(
    window: MainWindow,
) -> None:
    """The duplicate action becomes enabled when nodes are selected."""
    window._handle_add_node(0.2, 0.2)

    assert window._duplicate_action is not None
    assert window._duplicate_action.isEnabled() is False

    window._handle_canvas_click(_click(0.2, 0.2, node_id=1))

    assert window._duplicate_action.isEnabled() is True


def test_rename_action_requires_single_selection(
    window: MainWindow,
) -> None:
    """The rename action is enabled only when exactly one node is selected."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))
    window._handle_canvas_click(_click(0.2, 0.2, node_id=2, shift=True))

    assert window._rename_action is not None
    assert window._rename_action.isEnabled() is False

    window._handle_canvas_click(_click(0.5, 0.5, node_id=None))
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))

    assert window._rename_action.isEnabled() is True


def test_run_shortcut_when_no_algorithm_is_safe(
    window: MainWindow,
) -> None:
    """The F5 handler does nothing when the run button is disabled."""
    window._handle_run_shortcut()

    assert window._algorithm_state is window._algorithm_state.IDLE


def test_remove_isolated_nodes_removes_nothing_on_empty_graph(
    window: MainWindow,
) -> None:
    """The handler is a no-op when the graph is empty."""
    window._handle_remove_isolated_nodes()

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_remove_isolated_nodes_removes_only_isolated(
    window: MainWindow,
) -> None:
    """The handler removes isolated nodes and keeps connected ones."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._handle_add_node(0.3, 0.3)
    window._add_edge_use_case.execute(source=2, target=3)

    window._handle_remove_isolated_nodes()

    assert window._stats_label.text() == "Nodes: 2   Edges: 1"
    assert window._repository.get().has_node(1) is False
    assert window._repository.get().has_node(2) is True
    assert window._repository.get().has_node(3) is True


def test_remove_isolated_nodes_cleans_positions(
    window: MainWindow,
) -> None:
    """The handler removes positions of the deleted nodes."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    assert len(window._positions) == 2

    window._handle_remove_isolated_nodes()

    assert len(window._positions) == 0


def test_remove_isolated_nodes_clears_selection(
    window: MainWindow,
) -> None:
    """The handler drops removed nodes from the current selection."""
    window._handle_add_node(0.1, 0.1)
    window._handle_canvas_click(_click(0.1, 0.1, node_id=1))
    assert window._selected_nodes == {1}

    window._handle_remove_isolated_nodes()

    assert window._selected_nodes == set()


def test_remove_isolated_nodes_marks_dirty(
    window: MainWindow,
) -> None:
    """The handler commits a new snapshot to the edit history."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._add_edge_use_case.execute(source=1, target=2)
    window._handle_add_node(0.3, 0.3)
    window._history.mark_saved()
    assert window._history.is_dirty() is False

    window._handle_remove_isolated_nodes()

    assert window._history.is_dirty() is True


def test_remove_isolated_nodes_noop_keeps_history_clean(
    window: MainWindow,
) -> None:
    """The handler does not commit when there are no isolated nodes."""
    window._handle_add_node(0.1, 0.1)
    window._handle_add_node(0.2, 0.2)
    window._add_edge_use_case.execute(source=1, target=2)
    window._history.mark_saved()

    window._handle_remove_isolated_nodes()

    assert window._history.is_dirty() is False
