"""Use case for adding a node to the graph."""

from domain.entities.node import Node
from domain.interfaces.graph_repository import GraphRepository


class AddNodeUseCase:
    """Adds a new node to the graph stored in the repository.

    The use case rejects an id that already exists. This keeps the
    invariant that node ids are unique within a graph and surfaces
    programming errors early rather than silently replacing data.
    """

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the use case.

        Args:
            repository: The repository holding the graph.
        """
        self._repository = repository

    def execute(self, node_id: int, label: str = "") -> Node:
        """Add a node to the graph.

        Args:
            node_id: Unique identifier of the new node.
            label: Optional human-readable name.

        Returns:
            The created node.

        Raises:
            ValueError: If a node with the given id already exists.
        """
        graph = self._repository.get()
        if graph.has_node(node_id):
            raise ValueError(f"Node {node_id} already exists")
        node = Node(id=node_id, label=label)
        graph.add_node(node)
        return node
