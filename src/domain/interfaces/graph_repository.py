"""Repository interface for persisting and retrieving a graph."""

from abc import ABC, abstractmethod

from domain.entities.graph import Graph


class GraphRepository(ABC):
    """Contract for storing and retrieving a single graph.

    Implementations decide where the graph lives: in memory, on disk,
    or in a remote service. The domain only depends on this contract.
    """

    @abstractmethod
    def get(self) -> Graph:
        """Return the currently stored graph.

        If no graph has been saved yet, returns an empty graph. This
        allows callers to work with a valid object without handling
        None or exceptions on every access.

        Returns:
            The stored graph, or an empty graph if none was saved.
        """
        raise NotImplementedError

    @abstractmethod
    def save(self, graph: Graph) -> None:
        """Store the given graph, replacing any previously stored one.

        Args:
            graph: The graph to store.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove the stored graph and reset the repository to empty state."""
        raise NotImplementedError
