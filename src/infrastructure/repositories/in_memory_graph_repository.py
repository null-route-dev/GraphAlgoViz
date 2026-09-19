"""In-memory implementation of the GraphRepository contract."""

from domain.entities.graph import Graph
from domain.interfaces.graph_repository import GraphRepository


class InMemoryGraphRepository(GraphRepository):
    """Stores a graph in memory for the lifetime of the process.

    The repository holds a single graph instance. ``get`` returns a
    reference to that instance, so callers may mutate it directly for
    interactive editing. ``save`` replaces the stored graph with the
    provided one, which is useful when loading a different project.
    """

    def __init__(self) -> None:
        """Create a repository with an empty graph."""
        self._graph: Graph = Graph()

    def get(self) -> Graph:
        """Return the currently stored graph.

        Returns:
            The stored graph. If no graph has been saved, returns the
            initial empty graph.
        """
        return self._graph

    def save(self, graph: Graph) -> None:
        """Store the given graph, replacing any previously stored one.

        Args:
            graph: The graph to store.
        """
        self._graph = graph

    def clear(self) -> None:
        """Remove the stored graph and reset the repository to empty state."""
        self._graph = Graph()
