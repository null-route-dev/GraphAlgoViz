"""Use case for removing all nodes that have no incident edges."""

from domain.interfaces.graph_repository import GraphRepository


class RemoveIsolatedNodesUseCase:
    """Removes every node with no incident edges from the graph.

    A node is considered isolated when no edge references it, in
    either direction. Directed edges keep both endpoints attached:
    a node with only incoming edges is not isolated, because it still
    participates in the graph's connectivity.

    The use case is a no-op when the graph has no isolated nodes.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(self) -> list[int]:
        """Remove all isolated nodes and return their ids.

        Returns:
            The list of removed node ids, sorted ascending. Empty
            when the graph had no isolated nodes.
        """
        graph = self._repository.get()
        connected: set[int] = set()
        for edge in graph.edges():
            connected.add(edge.source)
            connected.add(edge.target)
        isolated = sorted(node.id for node in graph.nodes() if node.id not in connected)
        for node_id in isolated:
            graph.remove_node(node_id)
        return isolated
