"""Main application window."""

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QToolBar

from application.services.layout_service import LayoutService
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.ui.graph_canvas import GraphCanvas
from infrastructure.ui.interaction_mode import InteractionMode


class MainWindow(QMainWindow):
    """Top-level window hosting the graph canvas and toolbar.

    The window owns the current interaction mode. The canvas reads it
    on each mouse event but does not change it — mode switching is a
    UI concern, not a canvas concern.

    Args:
        repository: Source of the current graph.
        layout_service: Service that computes node positions.
    """

    def __init__(
        self,
        repository: GraphRepository,
        layout_service: LayoutService,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._layout_service = layout_service
        self._positions = layout_service.circular(repository.get())
        self._mode = InteractionMode.SELECT

        self.setWindowTitle("GraphAlgoViz")
        self.resize(900, 700)

        self._canvas = GraphCanvas(self)
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

        Args:
            mode: The mode to activate.
        """
        self._mode = mode
        self._status_bar.showMessage(f"Mode: {mode.display_name}")

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
        self._status_bar.showMessage(f"Mode: {self._mode.display_name}")

    def _refresh_canvas(self) -> None:
        """Redraw the canvas from the current graph and positions."""
        self._canvas.draw_graph(self._repository.get(), self._positions)
