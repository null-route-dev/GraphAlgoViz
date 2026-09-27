"""Main application window."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QDockWidget, QMainWindow, QToolBar

from application.algorithms.registry import AlgorithmRegistry
from application.algorithms.step_result import StepResult
from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from domain.value_objects.position import Position
from infrastructure.animation.algorithm_animator import AlgorithmAnimator
from infrastructure.ui.algorithm_panel import AlgorithmPanel, AlgorithmState
from infrastructure.ui.graph_canvas import GraphCanvas
from infrastructure.ui.interaction_mode import InteractionMode

MESSAGE_TIMEOUT_MS = 2000
DEFAULT_SPEED = 5
BASE_INTERVAL_MS = 1000


class MainWindow(QMainWindow):
    """Top-level window hosting the canvas, toolbar, and algorithm panel.

    The window owns the current interaction mode, the pending edge
    source, the node being dragged, the node positions, and the
    algorithm state. It dispatches canvas clicks to use cases or to
    the animator, and reflects algorithm progress in the panel and
    the canvas.

    Args:
        repository: Source of the current graph.
        layout_service: Service that computes initial node positions.
        registry: Registry of available graph algorithms.
        add_node_use_case: Use case for adding a node.
        add_edge_use_case: Use case for adding an edge.
        remove_node_use_case: Use case for removing a node.
    """

    def __init__(
        self,
        repository: GraphRepository,
        layout_service: LayoutService,
        registry: AlgorithmRegistry,
        add_node_use_case: AddNodeUseCase,
        add_edge_use_case: AddEdgeUseCase,
        remove_node_use_case: RemoveNodeUseCase,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._layout_service = layout_service
        self._registry = registry
        self._add_node_use_case = add_node_use_case
        self._add_edge_use_case = add_edge_use_case
        self._remove_node_use_case = remove_node_use_case

        self._positions = layout_service.circular(repository.get())
        self._mode = InteractionMode.SELECT
        self._pending_edge_source: int | None = None
        self._drag_node: int | None = None
        self._algorithm_state = AlgorithmState.IDLE
        self._current_interval_ms = BASE_INTERVAL_MS // DEFAULT_SPEED

        self.setWindowTitle("GraphAlgoViz")
        self.resize(1100, 700)

        self._canvas = GraphCanvas(
            self,
            on_click=self._handle_canvas_click,
            on_drag_move=self._handle_canvas_drag_move,
            on_drag_end=self._handle_canvas_drag_end,
        )
        self.setCentralWidget(self._canvas)

        self._animator = AlgorithmAnimator(self)
        self._animator.step_ready.connect(self._on_step_ready)
        self._animator.finished.connect(self._on_algorithm_finished)

        self._mode_actions: list[QAction] = []
        self._build_toolbar()
        self._build_status_bar()
        self._build_algorithm_panel()
        self._refresh_canvas()
        self._sync_available_nodes()

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
        """Create the status bar and show the initial mode."""
        self._status_bar = self.statusBar()
        self._restore_mode_message()

    def _build_algorithm_panel(self) -> None:
        """Create the algorithm panel and dock it on the right."""
        self._panel = AlgorithmPanel(self._registry, self)
        self._panel.run_requested.connect(self._on_run_requested)
        self._panel.pause_requested.connect(self._on_pause_requested)
        self._panel.step_requested.connect(self._on_step_requested)
        self._panel.reset_requested.connect(self._on_reset_requested)
        self._panel.speed_changed.connect(self._on_speed_changed)

        dock = QDockWidget("Algorithm", self)
        dock.setWidget(self._panel)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

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

    def _handle_canvas_click(
        self,
        x: float,
        y: float,
        node_id: int | None,
    ) -> None:
        """Dispatch a canvas click according to the active mode.

        Clicks are ignored while an algorithm is running or paused.

        Args:
            x: Horizontal coordinate of the click in the unit square.
            y: Vertical coordinate of the click in the unit square.
            node_id: Id of the node under the cursor, or None.
        """
        if self._algorithm_state in (
            AlgorithmState.RUNNING,
            AlgorithmState.PAUSED,
        ):
            return
        if self._mode is InteractionMode.SELECT:
            self._drag_node = node_id
        elif self._mode is InteractionMode.ADD_NODE:
            self._handle_add_node(x, y)
        elif self._mode is InteractionMode.ADD_EDGE:
            self._handle_add_edge(node_id)
        elif self._mode is InteractionMode.DELETE:
            self._handle_delete(node_id)

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
        self._sync_available_nodes()
        self._refresh_canvas()
        self._show_temporary_message(f"Added node {node.id}")

    def _handle_add_edge(self, node_id: int | None) -> None:
        """Add an edge between two consecutively clicked nodes.

        The first click stores the source; the second creates the edge.
        Clicking empty space cancels a pending source. Clicking the
        same node twice also cancels, since self-loops are not part of
        the editing flow.

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
        self._add_edge_use_case.execute(source=source, target=node_id)
        self._refresh_canvas()
        self._show_temporary_message(f"Added edge {source} -> {node_id}")

    def _handle_delete(self, node_id: int | None) -> None:
        """Remove the node under the cursor, if any.

        Args:
            node_id: Id of the node under the cursor, or None.
        """
        if node_id is None:
            self._show_temporary_message("Delete: no node under cursor")
            return
        self._remove_node_use_case.execute(node_id=node_id)
        self._positions.pop(node_id, None)
        if self._pending_edge_source == node_id:
            self._pending_edge_source = None
        self._sync_available_nodes()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted node {node_id}")

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
        if self._algorithm_state is AlgorithmState.PAUSED:
            self._animator.resume()
            self._algorithm_state = AlgorithmState.RUNNING
            self._panel.set_state(AlgorithmState.RUNNING)
            self._set_editing_enabled(False)
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

    def _on_pause_requested(self) -> None:
        """Pause the running algorithm."""
        self._animator.pause()
        self._algorithm_state = AlgorithmState.PAUSED
        self._panel.set_state(AlgorithmState.PAUSED)

    def _on_step_requested(self) -> None:
        """Advance the paused algorithm by one step."""
        self._animator.step_once()

    def _on_reset_requested(self) -> None:
        """Discard the current algorithm and return to idle."""
        self._animator.reset()
        self._algorithm_state = AlgorithmState.IDLE
        self._panel.set_state(AlgorithmState.IDLE)
        self._panel.set_info("")
        self._set_editing_enabled(True)
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
        )

    def _on_algorithm_finished(self) -> None:
        """Switch to the finished state when the algorithm completes."""
        self._algorithm_state = AlgorithmState.FINISHED
        self._panel.set_state(AlgorithmState.FINISHED)
        self._set_editing_enabled(True)

    def _refresh_canvas(self) -> None:
        """Redraw the canvas from the current graph and positions."""
        self._canvas.draw_graph(self._repository.get(), self._positions)
