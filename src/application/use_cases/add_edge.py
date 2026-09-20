"""Use case for adding an edge to the graph."""

from domain.entities.edge import Edge
from domain.interfaces.graph_repository import GraphRepository


class AddEdgeUseCase:
    """Adds a new edge between two existing nodes.

    Both endpoints must already exist. The use case does not create
    missing nodes implicitly, because that would hide typos in the UI.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(
        self,
        source: int,
        target: int,
        weight: float = 1.0,
        directed: bool = False,
    ) -> Edge:
        """Add an edge between two nodes.

        Args:
            source: Identifier of the source node.
            target: Identifier of the target node.
            weight: Numeric weight of the edge.
            directed: Whether the edge has a direction.

        Returns:
            The created edge.

        Raises:
            ValueError: If either endpoint does not exist.
        """
        graph = self._repository.get()
        edge = Edge(source=source, target=target, weight=weight, directed=directed)
        graph.add_edge(edge)
        return edge
