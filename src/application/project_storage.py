"""Interface for persisting a graph project to a file."""

from abc import ABC, abstractmethod
from pathlib import Path

from domain.entities.graph import Graph
from domain.value_objects.position import Position


class ProjectStorageError(Exception):
    """Raised when a project cannot be saved or loaded."""


class ProjectStorage(ABC):
    """Contract for saving and loading a graph project.

    A project is a graph together with the positions of its nodes.
    The positions are stored alongside the graph because they are
    part of what the user built and expects to see after reopening
    a file. Implementations decide the file format and the exact
    layout of the data.
    """

    @abstractmethod
    def save(
        self,
        graph: Graph,
        positions: dict[int, Position],
        path: Path,
    ) -> None:
        """Write the project to the given path.

        Args:
            graph: The graph to save.
            positions: Node positions in the unit square.
            path: Destination file path.

        Raises:
            ProjectStorageError: If the project cannot be written.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, path: Path) -> tuple[Graph, dict[int, Position]]:
        """Read the project from the given path.

        Args:
            path: Source file path.

        Returns:
            A tuple of the graph and its node positions.

        Raises:
            ProjectStorageError: If the project cannot be read.
        """
        raise NotImplementedError
