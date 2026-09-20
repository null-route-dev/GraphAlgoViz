"""Use case for removing a node from the graph."""

from domain.interfaces.graph_repository import GraphRepository


class RemoveNodeUseCase:
    """Removes a node and all edges incident to it.

    Removing a node silently also removes its edges. This is the only
    consistent behaviour: an edge whose endpoint is gone cannot exist.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(self, node_id: int) -> None:
        """Remove the node with the given id.

        Args:
            node_id: Identifier of the node to remove.

        Raises:
            KeyError: If the node does not exist.
        """
        graph = self._repository.get()
        graph.remove_node(node_id)
