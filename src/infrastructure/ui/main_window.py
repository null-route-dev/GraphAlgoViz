"""Main application window."""

from PySide6.QtWidgets import QMainWindow

from application.services.layout_service import LayoutService
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.ui.graph_canvas import GraphCanvas


class MainWindow(QMainWindow):
    """Top-level window hosting the graph canvas.

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

        self.setWindowTitle("GraphAlgoViz")
        self.resize(900, 700)
        self._canvas = GraphCanvas(self)
        self.setCentralWidget(self._canvas)
        self._canvas.draw_graph(self._repository.get(), self._positions)
