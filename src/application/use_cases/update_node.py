"""Use case for updating the label of an existing node."""

from domain.entities.node import Node
from domain.interfaces.graph_repository import GraphRepository


class UpdateNodeUseCase:
    """Replaces an existing node with a new one of the same id.

    Node is a frozen dataclass, so its label cannot be changed in
    place. The use case writes a new node with the same id and the
    new label. Graph.add_node replaces the existing entry, leaving
    edges untouched, since they reference node ids and not node
    objects.

    Changing a node's id is intentionally not supported: it would
    invalidate every edge that references it.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(self, node_id: int, label: str) -> Node:
        """Set the label of an existing node.

        Args:
            node_id: Identifier of the node to update.
            label: New label of the node.

        Returns:
            The updated node.

        Raises:
            KeyError: If the node does not exist.
        """
        graph = self._repository.get()
        if not graph.has_node(node_id):
            raise KeyError(f"Node {node_id} does not exist")
        new_node = Node(id=node_id, label=label)
        graph.add_node(new_node)
        return new_node
