"""GraphAlgoViz entry point."""

import sys

from PySide6.QtWidgets import QApplication

from application.algorithms.registry import build_default_registry
from application.services.layout_service import LayoutService
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)
from infrastructure.ui.main_window import MainWindow


def main() -> None:
    """Assemble dependencies and start the application."""
    repository = InMemoryGraphRepository()
    layout_service = LayoutService()
    registry = build_default_registry()

    add_node_use_case = AddNodeUseCase(repository)
    add_edge_use_case = AddEdgeUseCase(repository)
    remove_node_use_case = RemoveNodeUseCase(repository)
    remove_edge_use_case = RemoveEdgeUseCase(repository)

    app = QApplication(sys.argv)
    window = MainWindow(
        repository=repository,
        layout_service=layout_service,
        registry=registry,
        add_node_use_case=add_node_use_case,
        add_edge_use_case=add_edge_use_case,
        remove_node_use_case=remove_node_use_case,
        remove_edge_use_case=remove_edge_use_case,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
