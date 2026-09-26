"""Main application window."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QToolBar

from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from domain.value_objects.position import Position
from infrastructure.ui.graph_canvas import GraphCanvas
from infrastructure.ui.interaction_mode import InteractionMode

MESSAGE_TIMEOUT_MS = 2000


class MainWindow(QMainWindow):
    """Top-level window hosting the graph canvas and toolbar.

    The window owns the current interaction mode, the pending edge
    source for the ADD_EDGE mode, and the mapping from node id to
    position on the canvas. It translates canvas clicks into use case
    calls and refreshes the canvas afterwards.

    Args:
        repository: Source of the current graph.
        layout_service: Service that computes initial node positions.
        add_node_use_case: Use case for adding a node.
        add_edge_use_case: Use case for adding an edge.
        remove_node_use_case: Use case for removing a node.
    """

    def __init__(
        self,
        repository: GraphRepository,
        layout_service: LayoutService,
        add_node_use_case: AddNodeUseCase,
        add_edge_use_case: AddEdgeUseCase,
        remove_node_use_case: RemoveNodeUseCase,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._layout_service = layout_service
        self._add_node_use_case = add_node_use_case
        self._add_edge_use_case = add_edge_use_case
        self._remove_node_use_case = remove_node_use_case

        self._positions = layout_service.circular(repository.get())
        self._mode = InteractionMode.SELECT
        self._pending_edge_source: int | None = None

        self.setWindowTitle("GraphAlgoViz")
        self.resize(900, 700)

        self._canvas = GraphCanvas(self, on_click=self._handle_canvas_click)
        self.setCentralWidget(self._canvas)

        self._build_toolbar()
        self._build_status_bar()
        self._refresh_canvas()

    @property
    def mode(self) -> InteractionMode:
        """The currently selected interaction mode.

        Returns:
            The active mode.
        """
        return self._mode

    def set_mode(self, mode: InteractionMode) -> None:
        """Switch the interaction mode.

        Clears any pending edge source so that the next click in
        ADD_EDGE mode starts a fresh pair.

        Args:
            mode: The mode to activate.
        """
        self._mode = mode
        self._pending_edge_source = None
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

    def _build_status_bar(self) -> None:
        """Create the status bar and show the initial mode."""
        self._status_bar = self.statusBar()
        self._restore_mode_message()

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

    def _handle_canvas_click(
        self,
        x: float,
        y: float,
        node_id: int | None,
    ) -> None:
        """Dispatch a canvas click according to the active mode.

        Args:
            x: Horizontal coordinate of the click in the unit square.
            y: Vertical coordinate of the click in the unit square.
            node_id: Id of the node under the cursor, or None.
        """
        if self._mode is InteractionMode.ADD_NODE:
            self._handle_add_node(x, y)
        elif self._mode is InteractionMode.ADD_EDGE:
            self._handle_add_edge(node_id)
        elif self._mode is InteractionMode.DELETE:
            self._handle_delete(node_id)

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
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted node {node_id}")

    def _refresh_canvas(self) -> None:
        """Redraw the canvas from the current graph and positions."""
        self._canvas.draw_graph(self._repository.get(), self._positions)
