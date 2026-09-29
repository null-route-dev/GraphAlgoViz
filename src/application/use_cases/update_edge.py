"""Use case for updating the attributes of an existing edge."""

from domain.entities.edge import Edge
from domain.interfaces.graph_repository import GraphRepository


class UpdateEdgeUseCase:
    """Replaces an existing edge with a new one of the same endpoints.

    Edge is a frozen dataclass, so its attributes cannot be changed in
    place. The use case removes the old edge and adds a new one with
    the same source and target, but with the weight and direction
    taken from the arguments. For undirected edges, the order of
    source and target does not matter for the lookup.
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
        weight: float,
        directed: bool,
    ) -> Edge:
        """Update the weight and direction of an existing edge.

        Args:
            source: Identifier of one endpoint.
            target: Identifier of the other endpoint.
            weight: New weight of the edge.
            directed: New direction flag of the edge.

        Returns:
            The new edge with the updated attributes.

        Raises:
            KeyError: If no edge between the two nodes exists.
        """
        graph = self._repository.get()
        old_edge = self._find_edge(source, target)
        graph.remove_edge(old_edge.source, old_edge.target)
        new_edge = Edge(
            source=old_edge.source,
            target=old_edge.target,
            weight=weight,
            directed=directed,
        )
        graph.add_edge(new_edge)
        return new_edge

    def _find_edge(self, source: int, target: int) -> Edge:
        for edge in self._repository.get().edges():
            if edge.source == source and edge.target == target:
                return edge
            if not edge.directed and edge.source == target and edge.target == source:
                return edge
        raise KeyError(f"Edge {source} -> {target} does not exist")
