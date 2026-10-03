"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
)

from application.algorithms.registry import AlgorithmRegistry
from application.algorithms.step_result import StepResult
from application.project_storage import ProjectStorage, ProjectStorageError
from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from application.use_cases.update_edge import UpdateEdgeUseCase
from domain.entities.edge import Edge
from domain.interfaces.graph_repository import GraphRepository
from domain.value_objects.position import Position
from infrastructure.animation.algorithm_animator import AlgorithmAnimator
from infrastructure.ui.algorithm_panel import AlgorithmPanel, AlgorithmState
from infrastructure.ui.dialogs.edge_attributes_dialog import (
    EdgeAttributesDialog,
)
from infrastructure.ui.graph_canvas import GraphCanvas
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.theme import apply_theme

MESSAGE_TIMEOUT_MS = 2000
DEFAULT_SPEED = 5
BASE_INTERVAL_MS = 1000

PROJECT_FILTER = "GraphAlgoViz project (*.gaviz);;All files (*)"
PROJECT_SUFFIX = ".gaviz"

UNSAVED_TITLE = "Unsaved changes"
UNSAVED_TEXT = "The project has unsaved changes. Save them before continuing?"

APP_NAME = "GraphAlgoViz"
APP_VERSION = "0.1.0"
ABOUT_TITLE = f"About {APP_NAME}"
ABOUT_TEXT = (
    f"<h3>{APP_NAME} {APP_VERSION}</h3>"
    "<p>Interactive graph editor with step-by-step algorithm "
    "visualization.</p>"
    "<p>Built with Clean Architecture: domain, application, "
    "infrastructure, presentation.</p>"
    "<p>Licensed under the MIT License.</p>"
)

DEFAULT_DARK = True


class MainWindow(QMainWindow):
    """Top-level window hosting the canvas, toolbar, and algorithm panel.

    The window owns the current interaction mode, the pending edge
    source, the node being dragged, the node positions, the algorithm
    state, the path of the last saved or opened project, a dirty flag,
    and the current theme.

    Any mutation of the graph or of node positions marks the project
    as dirty. Saving, loading, and creating a new project reset the
    flag. New, Open, and window close ask the user to save first if
    the project is dirty.

    Editing is locked while an algorithm is loaded, in any state
    except IDLE. This keeps the algorithm's history consistent with
    the graph it was computed against. Reset returns to IDLE and
    unlocks editing.

    The status bar shows the current mode on the left and a permanent
    graph summary (node and edge counts) on the right. The algorithm
    panel is docked on the right and can be hidden or restored from
    the View menu. The View menu also toggles the theme.

    Args:
        repository: Source of the current graph.
        layout_service: Service that computes initial node positions.
        registry: Registry of available graph algorithms.
        storage: Storage for saving and loading projects.
        add_node_use_case: Use case for adding a node.
        add_edge_use_case: Use case for adding an edge.
        remove_node_use_case: Use case for removing a node.
        remove_edge_use_case: Use case for removing an edge.
        update_edge_use_case: Use case for updating edge attributes.
        dark: Whether to start with the dark theme.
    """

    def __init__(
        self,
        repository: GraphRepository,
        layout_service: LayoutService,
        registry: AlgorithmRegistry,
        storage: ProjectStorage,
        add_node_use_case: AddNodeUseCase,
        add_edge_use_case: AddEdgeUseCase,
        remove_node_use_case: RemoveNodeUseCase,
        remove_edge_use_case: RemoveEdgeUseCase,
        update_edge_use_case: UpdateEdgeUseCase,
        dark: bool = DEFAULT_DARK,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._layout_service = layout_service
        self._registry = registry
        self._storage = storage
        self._add_node_use_case = add_node_use_case
        self._add_edge_use_case = add_edge_use_case
        self._remove_node_use_case = remove_node_use_case
        self._remove_edge_use_case = remove_edge_use_case
        self._update_edge_use_case = update_edge_use_case

        self._positions = layout_service.circular(repository.get())
        self._mode = InteractionMode.SELECT
        self._pending_edge_source: int | None = None
        self._drag_node: int | None = None
        self._algorithm_state = AlgorithmState.IDLE
        self._current_interval_ms = BASE_INTERVAL_MS // DEFAULT_SPEED
        self._current_path: Path | None = None
        self._dirty = False
        self._dark = dark

        self.setWindowTitle(APP_NAME)
        self.resize(1100, 700)

        self._canvas = GraphCanvas(
            self,
            on_click=self._handle_canvas_click,
            on_drag_move=self._handle_canvas_drag_move,
            on_drag_end=self._handle_canvas_drag_end,
            dark=dark,
        )
        self.setCentralWidget(self._canvas)

        self._animator = AlgorithmAnimator(self)
        self._animator.step_ready.connect(self._on_step_ready)
        self._animator.finished.connect(self._on_algorithm_finished)

        self._mode_actions: list[QAction] = []
        self._view_menu: QMenu | None = None
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_algorithm_panel()
        self._add_theme_action()
        self._refresh_canvas()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._update_step_availability()

    @property
    def mode(self) -> InteractionMode:
        """The currently selected interaction mode.

        Returns:
            The active mode.
        """
        return self._mode

    def set_mode(self, mode: InteractionMode) -> None:
        """Switch the interaction mode.

        Clears any pending edge source and any active drag so that
        the next mouse event starts from a clean state.

        Args:
            mode: The mode to activate.
        """
        self._mode = mode
        self._pending_edge_source = None
        self._drag_node = None
        self._restore_mode_message()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Confirm unsaved changes before closing the window.

        Args:
            event: The close event.
        """
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def _build_menu(self) -> None:
        """Create the menu bar with File, View, and Help actions."""
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._handle_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._handle_open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._handle_save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._handle_save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        self._view_menu = self.menuBar().addMenu("&View")

        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction(f"&About {APP_NAME}", self)
        about_action.triggered.connect(self._handle_about)
        help_menu.addAction(about_action)

    def _build_toolbar(self) -> None:
        """Create the toolbar with mode-switching actions."""
        toolbar = QToolBar("Tools", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        group = QActionGroup(self)
        group.setExclusive(True)

        modes = (
            InteractionMode.SELECT,
            InteractionMode.ADD_NODE,
            InteractionMode.ADD_EDGE,
            InteractionMode.DELETE,
        )
        for mode in modes:
            action = QAction(mode.display_name, self)
            action.setCheckable(True)
            action.setChecked(mode is self._mode)
            action.triggered.connect(lambda checked=False, m=mode: self.set_mode(m))
            group.addAction(action)
            toolbar.addAction(action)
            self._mode_actions.append(action)

    def _build_status_bar(self) -> None:
        """Create the status bar with mode and graph stats."""
        self._status_bar = self.statusBar()
        self._stats_label = QLabel("", self)
        self._stats_label.setContentsMargins(0, 0, 8, 0)
        self._status_bar.addPermanentWidget(self._stats_label)
        self._restore_mode_message()

    def _build_algorithm_panel(self) -> None:
        """Create the algorithm panel and dock it on the right."""
        self._panel = AlgorithmPanel(self._registry, self)
        self._panel.run_requested.connect(self._on_run_requested)
        self._panel.pause_requested.connect(self._on_pause_requested)
        self._panel.step_requested.connect(self._on_step_requested)
        self._panel.step_back_requested.connect(self._on_step_back_requested)
        self._panel.reset_requested.connect(self._on_reset_requested)
        self._panel.speed_changed.connect(self._on_speed_changed)

        dock = QDockWidget("Algorithm", self)
        dock.setWidget(self._panel)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        if self._view_menu is not None:
            self._view_menu.addAction(dock.toggleViewAction())

    def _add_theme_action(self) -> None:
        """Add the theme toggle to the View menu."""
        if self._view_menu is None:
            return
        self._view_menu.addSeparator()
        self._dark_theme_action = QAction("Dark theme", self)
        self._dark_theme_action.setCheckable(True)
        self._dark_theme_action.setChecked(self._dark)
        self._dark_theme_action.triggered.connect(self._handle_toggle_theme)
        self._view_menu.addAction(self._dark_theme_action)

    def _handle_toggle_theme(self, checked: bool) -> None:
        """Switch between dark and light themes.

        Args:
            checked: True for the dark theme, False for the light one.
        """
        self._dark = checked
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, checked)
        self._canvas.set_dark(checked)
        self._refresh_canvas()

    def _restore_mode_message(self) -> None:
        """Show the current mode in the status bar."""
        self._status_bar.showMessage(f"Mode: {self._mode.display_name}")

    def _show_temporary_message(self, text: str) -> None:
        """Show a short-lived status bar message, then restore the mode.

        Args:
            text: The message to display.
        """
        self._status_bar.showMessage(text)
        QTimer.singleShot(MESSAGE_TIMEOUT_MS, self._restore_mode_message)

    def _set_editing_enabled(self, enabled: bool) -> None:
        """Enable or disable the mode-switching toolbar actions.

        Args:
            enabled: True to allow mode switching, False to forbid it.
        """
        for action in self._mode_actions:
            action.setEnabled(enabled)

    def _sync_available_nodes(self) -> None:
        """Update the panel's start node list from the current graph."""
        node_ids = [node.id for node in self._repository.get().nodes()]
        self._panel.set_available_nodes(node_ids)

    def _update_graph_stats(self) -> None:
        """Update the permanent graph summary in the status bar."""
        graph = self._repository.get()
        nodes = graph.node_count
        edges = graph.edge_count
        self._stats_label.setText(f"Nodes: {nodes}   Edges: {edges}")

    def _update_step_availability(self) -> None:
        """Refresh the panel's step buttons from the animator state."""
        self._panel.set_step_availability(
            can_step_back=self._animator.can_step_back,
            can_step_forward=self._animator.can_step_forward,
        )

    def _update_window_title(self) -> None:
        """Update the window title to reflect file and dirty state."""
        title = APP_NAME
        if self._current_path is not None:
            title = f"{title} - {self._current_path.name}"
        if self._dirty:
            title = f"{title} *"
        self.setWindowTitle(title)

    def _mark_dirty(self) -> None:
        """Mark the project as having unsaved changes."""
        if not self._dirty:
            self._dirty = True
            self._update_window_title()

    def _clear_dirty(self) -> None:
        """Mark the project as clean after a successful save or load."""
        if self._dirty:
            self._dirty = False
            self._update_window_title()

    def _confirm_discard_changes(self) -> bool:
        """Ask the user what to do with unsaved changes.

        Returns:
            True if it is safe to proceed (no changes, or the user
            saved them, or the user explicitly discarded them).
            False if the user cancelled.
        """
        if not self._dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle(UNSAVED_TITLE)
        box.setText(UNSAVED_TEXT)
        box.setIcon(QMessageBox.Icon.Warning)
        save_button = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard_button = box.addButton(
            "Discard", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return self._handle_save_project()
        if clicked is discard_button:
            return True
        if clicked is cancel_button:
            return False
        return False

    def _handle_about(self) -> None:
        """Show a modal About dialog."""
        QMessageBox.about(self, ABOUT_TITLE, ABOUT_TEXT)

    def _reset_algorithm(self) -> None:
        """Stop and clear any running algorithm."""
        self._animator.reset()
        self._algorithm_state = AlgorithmState.IDLE
        self._panel.set_state(AlgorithmState.IDLE)
        self._panel.set_info("")
        self._set_editing_enabled(True)
        self._update_step_availability()

    def _handle_new_project(self) -> None:
        """Reset the application to an empty project."""
        if not self._confirm_discard_changes():
            return
        self._repository.clear()
        self._positions = {}
        self._current_path = None
        self._pending_edge_source = None
        self._drag_node = None
        self._reset_algorithm()
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._clear_dirty()
        self._update_window_title()
        self._show_temporary_message("New project")

    def _handle_open_project(self) -> None:
        """Prompt for a file and load the project from it."""
        if not self._confirm_discard_changes():
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open project", "", PROJECT_FILTER
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            graph, positions = self._storage.load(path)
        except ProjectStorageError as exc:
            QMessageBox.warning(self, "Open failed", str(exc))
            return
        self._repository.save(graph)
        self._positions = positions
        self._current_path = path
        self._pending_edge_source = None
        self._drag_node = None
        self._reset_algorithm()
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._clear_dirty()
        self._update_window_title()
        self._show_temporary_message(f"Opened {path.name}")

    def _handle_save_project(self) -> bool:
        """Save the current project to its path or prompt for one.

        Returns:
            True if the project was saved, False if the user
            cancelled or the save failed.
        """
        if self._current_path is None:
            return self._handle_save_project_as()
        return self._save_to(self._current_path)

    def _handle_save_project_as(self) -> bool:
        """Prompt for a path and save the current project there.

        Returns:
            True if the project was saved, False if the user
            cancelled or the save failed.
        """
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Save project", "", PROJECT_FILTER
        )
        if not path_str:
            return False
        path = Path(path_str)
        if path.suffix != PROJECT_SUFFIX:
            path = path.with_suffix(PROJECT_SUFFIX)
        return self._save_to(path)

    def _save_to(self, path: Path) -> bool:
        """Write the current project to the given path.

        Args:
            path: Destination file path.

        Returns:
            True if the project was saved, False otherwise.
        """
        try:
            self._storage.save(self._repository.get(), self._positions, path)
        except ProjectStorageError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return False
        self._current_path = path
        self._clear_dirty()
        self._update_window_title()
        self._show_temporary_message(f"Saved to {path.name}")
        return True

    def _handle_canvas_click(
        self,
        x: float,
        y: float,
        node_id: int | None,
        edge: tuple[int, int] | None,
    ) -> None:
        """Dispatch a canvas click according to the active mode.

        Clicks are ignored while any algorithm is loaded, since the
        graph must remain consistent with the algorithm's history.

        Args:
            x: Horizontal coordinate of the click in the unit square.
            y: Vertical coordinate of the click in the unit square.
            node_id: Id of the node under the cursor, or None.
            edge: Endpoints of the edge under the cursor, or None.
        """
        if self._algorithm_state is not AlgorithmState.IDLE:
            return
        if self._mode is InteractionMode.SELECT:
            if node_id is not None:
                self._drag_node = node_id
            elif edge is not None:
                self._handle_edit_edge(edge)
        elif self._mode is InteractionMode.ADD_NODE:
            self._handle_add_node(x, y)
        elif self._mode is InteractionMode.ADD_EDGE:
            self._handle_add_edge(node_id)
        elif self._mode is InteractionMode.DELETE:
            self._handle_delete(node_id, edge)

    def _handle_canvas_drag_move(self, x: float, y: float) -> None:
        """Move the node currently being dragged, if any.

        Args:
            x: Horizontal coordinate of the cursor in the unit square.
            y: Vertical coordinate of the cursor in the unit square.
        """
        if self._mode is not InteractionMode.SELECT:
            return
        if self._drag_node is None:
            return
        self._positions[self._drag_node] = Position(x=x, y=y)
        self._mark_dirty()
        self._refresh_canvas()

    def _handle_canvas_drag_end(self) -> None:
        """Finish any active drag."""
        self._drag_node = None

    def _handle_add_node(self, x: float, y: float) -> None:
        """Add a node at the clicked position.

        Args:
            x: Horizontal coordinate of the click.
            y: Vertical coordinate of the click.
        """
        graph = self._repository.get()
        new_id = graph.next_id()
        node = self._add_node_use_case.execute(node_id=new_id)
        self._positions[node.id] = Position(x=x, y=y)
        self._mark_dirty()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Added node {node.id}")

    def _handle_add_edge(self, node_id: int | None) -> None:
        """Add an edge between two consecutively clicked nodes.

        The first click stores the source. The second click opens a
        dialog for the edge attributes; if confirmed, the edge is
        created. Clicking empty space cancels a pending source.
        Clicking the same node twice also cancels, since self-loops
        are not part of the editing flow.

        Args:
            node_id: Id of the node under the cursor, or None.
        """
        if node_id is None:
            self._pending_edge_source = None
            self._show_temporary_message("Add edge: cancelled")
            return

        if self._pending_edge_source is None:
            self._pending_edge_source = node_id
            self._show_temporary_message(
                f"Add edge: source is node {node_id}, click target"
            )
            return

        if self._pending_edge_source == node_id:
            self._pending_edge_source = None
            self._show_temporary_message("Add edge: cancelled")
            return

        source = self._pending_edge_source
        self._pending_edge_source = None

        attributes = EdgeAttributesDialog.get_attributes(parent=self)
        if attributes is None:
            self._show_temporary_message("Add edge: cancelled")
            return

        self._add_edge_use_case.execute(
            source=source,
            target=node_id,
            weight=attributes.weight,
            directed=attributes.directed,
        )
        self._mark_dirty()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(
            f"Added edge {source} -> {node_id} (weight {attributes.weight:g})"
        )

    def _handle_edit_edge(self, edge: tuple[int, int]) -> None:
        """Open a dialog to change the attributes of an existing edge.

        Args:
            edge: Endpoints of the edge to edit.
        """
        source, target = edge
        current = self._find_edge(source, target)
        if current is None:
            return
        attributes = EdgeAttributesDialog.get_attributes(
            initial_weight=current.weight,
            initial_directed=current.directed,
            parent=self,
        )
        if attributes is None:
            self._show_temporary_message("Edit edge: cancelled")
            return
        self._update_edge_use_case.execute(
            source=source,
            target=target,
            weight=attributes.weight,
            directed=attributes.directed,
        )
        self._mark_dirty()
        self._refresh_canvas()
        self._show_temporary_message(
            f"Edge {source} -> {target} updated (weight {attributes.weight:g})"
        )

    def _find_edge(self, source: int, target: int) -> Edge | None:
        for edge in self._repository.get().edges():
            if edge.source == source and edge.target == target:
                return edge
            if not edge.directed and edge.source == target and edge.target == source:
                return edge
        return None

    def _handle_delete(
        self,
        node_id: int | None,
        edge: tuple[int, int] | None,
    ) -> None:
        """Remove the node or edge under the cursor.

        Nodes take priority over edges: if the click landed on a node,
        only the node is removed. Otherwise, if an edge was hit, that
        edge is removed.

        Args:
            node_id: Id of the node under the cursor, or None.
            edge: Endpoints of the edge under the cursor, or None.
        """
        if node_id is not None:
            self._handle_delete_node(node_id)
            return
        if edge is not None:
            self._handle_delete_edge(edge)
            return
        self._show_temporary_message("Delete: nothing under cursor")

    def _handle_delete_node(self, node_id: int) -> None:
        """Remove a node and all edges incident to it.

        Args:
            node_id: Id of the node to remove.
        """
        self._remove_node_use_case.execute(node_id=node_id)
        self._positions.pop(node_id, None)
        if self._pending_edge_source == node_id:
            self._pending_edge_source = None
        self._mark_dirty()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted node {node_id}")

    def _handle_delete_edge(self, edge: tuple[int, int]) -> None:
        """Remove the edge between two nodes.

        Args:
            edge: Endpoints of the edge to remove.
        """
        source, target = edge
        self._remove_edge_use_case.execute(source=source, target=target)
        self._mark_dirty()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted edge {source} -> {target}")

    def _on_run_requested(
        self,
        algorithm_id: str,
        start_node_id: int,
    ) -> None:
        """Start or resume an algorithm run.

        Args:
            algorithm_id: Identifier of the algorithm to run.
            start_node_id: Id of the node to start from.
        """
        if self._algorithm_state in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            self._animator.resume()
            self._algorithm_state = AlgorithmState.RUNNING
            self._panel.set_state(AlgorithmState.RUNNING)
            self._set_editing_enabled(False)
            self._update_step_availability()
            return

        graph = self._repository.get()
        try:
            algorithm = self._registry.create(algorithm_id, graph, start_node_id)
        except (KeyError, ValueError) as exc:
            self._show_temporary_message(str(exc))
            return

        self._mode = InteractionMode.SELECT
        self._pending_edge_source = None
        self._drag_node = None
        self._set_editing_enabled(False)
        self._algorithm_state = AlgorithmState.RUNNING
        self._panel.set_state(AlgorithmState.RUNNING)
        self._panel.set_info("")
        self._animator.start(algorithm, self._current_interval_ms)
        self._update_step_availability()

    def _on_pause_requested(self) -> None:
        """Pause the running algorithm."""
        self._animator.pause()
        self._algorithm_state = AlgorithmState.PAUSED
        self._panel.set_state(AlgorithmState.PAUSED)
        self._update_step_availability()

    def _on_step_requested(self) -> None:
        """Advance the paused or finished algorithm by one step."""
        if self._algorithm_state not in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            return
        self._animator.step_forward()
        if self._animator.can_step_forward:
            self._algorithm_state = AlgorithmState.PAUSED
        else:
            self._algorithm_state = AlgorithmState.FINISHED
        self._panel.set_state(self._algorithm_state)
        self._update_step_availability()

    def _on_step_back_requested(self) -> None:
        """Return to the previous state in the algorithm's history."""
        if self._algorithm_state not in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            return
        self._animator.step_back()
        self._algorithm_state = AlgorithmState.PAUSED
        self._panel.set_state(AlgorithmState.PAUSED)
        self._update_step_availability()

    def _on_reset_requested(self) -> None:
        """Discard the current algorithm and return to idle."""
        self._reset_algorithm()
        self._refresh_canvas()

    def _on_speed_changed(self, interval_ms: int) -> None:
        """Update the animation speed.

        Args:
            interval_ms: New delay between steps in milliseconds.
        """
        self._current_interval_ms = interval_ms
        self._animator.set_interval(interval_ms)

    def _on_step_ready(self, result: object) -> None:
        """Render the latest algorithm step.

        Args:
            result: A StepResult emitted by the animator.
        """
        if not isinstance(result, StepResult):
            return
        self._panel.set_info(result.info)
        self._canvas.draw_graph(
            graph=self._repository.get(),
            positions=self._positions,
            highlighted_nodes=result.visited,
            current_node=result.current,
            highlighted_edges=result.tree_edges,
            labels=result.labels,
            node_colors=result.node_colors,
        )
        self._update_step_availability()

    def _on_algorithm_finished(self) -> None:
        """Switch to the finished state when the algorithm completes.

        Editing stays locked: the user must Reset to modify the graph,
        since the algorithm's history refers to the current graph.
        """
        self._algorithm_state = AlgorithmState.FINISHED
        self._panel.set_state(AlgorithmState.FINISHED)
        self._update_step_availability()

    def _refresh_canvas(self) -> None:
        """Redraw the canvas from the current graph and positions."""
        self._canvas.draw_graph(self._repository.get(), self._positions)
