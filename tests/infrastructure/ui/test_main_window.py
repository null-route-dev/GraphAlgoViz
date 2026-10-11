"""Tests for the main application window."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent, QKeySequence

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
from infrastructure.settings import AppSettings
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.main_window import (
    APP_NAME,
    MODE_SHORTCUTS,
    MainWindow,
)


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[AppSettings]:
    """Return AppSettings backed by a temporary file."""
    qsettings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    yield AppSettings(qsettings)
    qsettings.clear()


@pytest.fixture
def window(qtbot: object, settings: AppSettings) -> Iterator[MainWindow]:
    """Return a fully wired MainWindow for testing.

    The window is closed in teardown. Before closing, the edit history
    is marked as saved so that ``closeEvent`` does not open a modal
    confirmation dialog — that dialog would block forever in offscreen
    mode, where no one can click its buttons.
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
        settings=settings,
        add_node_use_case=add_node,
        add_edge_use_case=add_edge,
        remove_node_use_case=remove_node,
        remove_edge_use_case=remove_edge,
        update_edge_use_case=update_edge,
    )
    _ = qtbot
    yield widget
    widget._history.mark_saved()
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
    assert window._history.is_dirty() is False
    assert "*" not in window.windowTitle()


def test_add_node_marks_dirty(window: MainWindow) -> None:
    """Adding a node marks the project as dirty."""
    window._handle_add_node(0.5, 0.5)

    assert window._history.is_dirty() is True
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
    window._handle_add_node(0.5, 0.5)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: False)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is False


def test_close_event_accepted_when_confirmed(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirming the dialog accepts the close event."""
    window._handle_add_node(0.5, 0.5)
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


def test_mode_shortcuts_map_is_complete() -> None:
    """Every interaction mode has a shortcut assigned."""
    for mode in InteractionMode:
        assert mode in MODE_SHORTCUTS


def test_mode_actions_have_shortcuts(window: MainWindow) -> None:
    """Each mode action carries the shortcut from MODE_SHORTCUTS."""
    for action in window._mode_actions:
        expected_mode = None
        for mode in InteractionMode:
            if action.text() == mode.display_name:
                expected_mode = mode
                break
        assert expected_mode is not None
        assert action.shortcut() == QKeySequence(MODE_SHORTCUTS[expected_mode])


def test_toggle_theme_persists_setting(
    window: MainWindow,
    settings: AppSettings,
) -> None:
    """Toggling the theme saves the choice through AppSettings."""
    settings.set_dark_theme(True)
    window._handle_toggle_theme(False)

    assert settings.dark_theme() is False


def test_toggle_theme_updates_flag(window: MainWindow) -> None:
    """Toggling the theme updates the window's internal flag."""
    window._handle_toggle_theme(False)

    assert window._dark is False


def test_undo_initially_disabled(window: MainWindow) -> None:
    """Undo is disabled when there is nothing to undo."""
    assert window._undo_action is not None
    assert window._undo_action.isEnabled() is False


def test_redo_initially_disabled(window: MainWindow) -> None:
    """Redo is disabled when there is nothing to redo."""
    assert window._redo_action is not None
    assert window._redo_action.isEnabled() is False


def test_undo_enabled_after_edit(window: MainWindow) -> None:
    """Undo becomes enabled after a mutation."""
    window._handle_add_node(0.5, 0.5)

    assert window._undo_action is not None
    assert window._undo_action.isEnabled() is True


def test_undo_reverts_add_node(window: MainWindow) -> None:
    """Undo removes the node added by the last edit."""
    window._handle_add_node(0.5, 0.5)
    assert window._stats_label.text() == "Nodes: 1   Edges: 0"

    window._handle_undo()

    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_redo_reapplies_add_node(window: MainWindow) -> None:
    """Redo restores the node removed by undo."""
    window._handle_add_node(0.5, 0.5)
    window._handle_undo()
    window._handle_redo()

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"


def test_undo_reverts_multiple_edits(window: MainWindow) -> None:
    """Undo walks back through the history one step at a time."""
    window._handle_add_node(0.5, 0.5)
    window._handle_add_node(0.6, 0.6)
    window._handle_add_node(0.7, 0.7)
    assert window._stats_label.text() == "Nodes: 3   Edges: 0"

    window._handle_undo()
    assert window._stats_label.text() == "Nodes: 2   Edges: 0"

    window._handle_undo()
    assert window._stats_label.text() == "Nodes: 1   Edges: 0"

    window._handle_undo()
    assert window._stats_label.text() == "Nodes: 0   Edges: 0"


def test_redo_becomes_disabled_after_new_edit(window: MainWindow) -> None:
    """A new edit after undo discards the redo tail."""
    window._handle_add_node(0.5, 0.5)
    window._handle_undo()
    assert window._redo_action is not None
    assert window._redo_action.isEnabled() is True

    window._handle_add_node(0.7, 0.7)

    assert window._redo_action.isEnabled() is False


def test_undo_to_saved_state_clears_dirty(window: MainWindow) -> None:
    """Undo back to the saved state removes the dirty indicator."""
    window._handle_add_node(0.5, 0.5)
    assert "*" in window.windowTitle()

    window._handle_undo()

    assert "*" not in window.windowTitle()


def test_new_project_clears_history(window: MainWindow) -> None:
    """File → New resets history and disables undo."""
    window._handle_add_node(0.5, 0.5)
    window._confirm_discard_changes = lambda: True  # type: ignore[method-assign]

    window._handle_new_project()

    assert window._undo_action is not None
    assert window._undo_action.isEnabled() is False
    assert window._history.is_dirty() is False


def test_undo_does_not_touch_algorithm_state(window: MainWindow) -> None:
    """Undo is ignored while an algorithm is loaded."""
    window._handle_add_node(0.5, 0.5)
    window._algorithm_state = window._algorithm_state.PAUSED
    window._set_editing_enabled(False)

    window._handle_undo()

    assert window._stats_label.text() == "Nodes: 1   Edges: 0"
