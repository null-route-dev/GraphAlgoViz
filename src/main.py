"""GraphAlgoViz entry point."""

import sys

from PySide6.QtWidgets import QApplication

from application.algorithms.registry import build_default_registry
from application.services.layout_service import LayoutService
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)
from infrastructure.ui.main_window import MainWindow


def main() -> None:
    """Assemble dependencies and start the application."""
    repository = InMemoryGraphRepository()
    layout_service = LayoutService()
    registry = build_default_registry()

    app = QApplication(sys.argv)
    window = MainWindow(repository, layout_service)
    window.show()
    _ = registry
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
