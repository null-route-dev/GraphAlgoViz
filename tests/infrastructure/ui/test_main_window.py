"""Tests for the main application window."""

from collections.abc import Iterator

import pytest
from PySide6.QtGui import QCloseEvent

from application.algorithms.registry import build_default_registry
from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from application.use_cases.update_edge import UpdateEdgeUseCase
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)
from infrastructure.serialization.json_project_storage import (
    JsonProjectStorage,
)
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.main_window import APP_NAME, MainWindow


@pytest.fixture
def window(qtbot: object) -> Iterator[MainWindow]:
    """Return a fully wired MainWindow for testing.

    The window is closed in teardown. Before closing, the dirty flag
    is cleared so that ``closeEvent`` does not open a modal confirmation
    dialog — that dialog would block forever in offscreen mode, where
    no one can click its buttons.
    """
    repository = InMemoryGraphRepository()
    layout_service = LayoutService()
    registry = build_default_registry()
    storage = JsonProjectStorage()

    add_node = AddNodeUseCase(repository)
    add_edge = AddEdgeUseCase(repository)
    remove_node = RemoveNodeUseCase(repository)
    remove_edge = RemoveEdgeUseCase(repository)
    update_edge = UpdateEdgeUseCase(repository)

    widget = MainWindow(
        repository=repository,
        layout_service=layout_service,
        registry=registry,
        storage=storage,
        add_node_use_case=add_node,
        add_edge_use_case=add_edge,
        remove_node_use_case=remove_node,
        remove_edge_use_case=remove_edge,
        update_edge_use_case=update_edge,
    )
    _ = qtbot
    yield widget
    widget._dirty = False
    widget.close()
    widget.deleteLater()


def test_initial_title_is_app_name(window: MainWindow) -> None:
    """A fresh window shows the app name in the title."""
    assert window.windowTitle() == APP_NAME


def test_initial_mode_is_select(window: MainWindow) -> None:
    """The window starts in SELECT mode."""
    assert window.mode is InteractionMode.SELECT


def test_initial_stats_show_zero(window: MainWindow) -> None:
    """The status bar shows zero nodes and zero edges."""
    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_new_window_is_clean(window: MainWindow) -> None:
    """A fresh window has no unsaved changes."""
    assert window._dirty is False
    assert "*" not in window.windowTitle()


def test_add_node_marks_dirty(window: MainWindow) -> None:
    """Adding a node marks the project as dirty."""
    window._handle_add_node(0.5, 0.5)

    assert window._dirty is True
    assert "*" in window.windowTitle()


def test_add_node_updates_stats(window: MainWindow) -> None:
    """Adding a node updates the status bar counters."""
    window._handle_add_node(0.5, 0.5)

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"


def test_delete_node_updates_stats(window: MainWindow) -> None:
    """Deleting a node updates the status bar counters."""
    window._handle_add_node(0.5, 0.5)
    window._handle_delete_node(1)

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_set_mode_updates_status(window: MainWindow) -> None:
    """Switching the mode updates the status bar message."""
    window.set_mode(InteractionMode.ADD_NODE)

    assert window.mode is InteractionMode.ADD_NODE
    assert "Add Node" in window._status_bar.currentMessage()


def test_clear_dirty_removes_asterisk(window: MainWindow) -> None:
    """_clear_dirty removes the dirty indicator from the title."""
    window._handle_add_node(0.5, 0.5)
    assert "*" in window.windowTitle()

    window._clear_dirty()

    assert "*" not in window.windowTitle()


def test_close_event_accepted_when_clean(window: MainWindow) -> None:
    """Closing a clean project accepts the event without prompting."""
    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()


def test_close_event_ignored_when_cancelled(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling the confirmation dialog ignores the close event."""
    window._dirty = True
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: False)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is False


def test_close_event_accepted_when_confirmed(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirming the dialog accepts the close event."""
    window._dirty = True
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()


def test_editing_locked_while_algorithm_loaded(window: MainWindow) -> None:
    """Clicks are ignored while an algorithm is loaded."""
    window._handle_add_node(0.5, 0.5)
    window._handle_add_node(0.6, 0.6)
    window._algorithm_state = window._algorithm_state.PAUSED

    window._handle_canvas_click(0.5, 0.5, node_id=1, edge=None)

    assert window._drag_node is None
