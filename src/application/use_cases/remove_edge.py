"""Use case for removing an edge from the graph."""

from domain.interfaces.graph_repository import GraphRepository


class RemoveEdgeUseCase:
    """Removes an edge between two nodes.

    For undirected edges, the order of arguments does not matter.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(self, source: int, target: int) -> None:
        """Remove the edge between two nodes.

        Args:
            source: Identifier of one endpoint.
            target: Identifier of the other endpoint.

        Raises:
            KeyError: If no matching edge exists.
        """
        graph = self._repository.get()
        graph.remove_edge(source, target)
