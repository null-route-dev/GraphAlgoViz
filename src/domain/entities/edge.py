"""Edge entity of the graph domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    """A connection between two nodes.

    For an undirected edge, source and target are interchangeable.
    For a directed edge, the connection goes from source to target.

    Args:
        source: Identifier of the source node.
        target: Identifier of the target node.
        weight: Numeric weight of the edge.
        directed: Whether the edge has a direction.
    """

    source: int
    target: int
    weight: float = 1.0
    directed: bool = False

    def connects(self, node_id: int) -> bool:
        """Return True if the edge is incident to the given node.

        Args:
            node_id: Identifier of the node to check.

        Returns:
            True if the node is one of the edge endpoints.
        """
        return node_id == self.source or node_id == self.target

    def other_end(self, node_id: int) -> int:
        """Return the node at the opposite end of the edge.

        Args:
            node_id: Identifier of the node at one end.

        Returns:
            Identifier of the node at the opposite end.

        Raises:
            ValueError: If the given node is not incident to this edge.
        """
        if node_id == self.source:
            return self.target
        if node_id == self.target:
            return self.source
        raise ValueError(f"Node {node_id} is not incident to edge {self}")
