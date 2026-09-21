"""Graph entity — the aggregate root of the domain."""

from domain.entities.edge import Edge
from domain.entities.node import Node


class Graph:
    """A collection of nodes and edges.

    Nodes are indexed by id. Edges are stored as a flat list, which keeps
    the model simple and is sufficient for interactive use.

    The graph tracks the highest node id ever assigned. Ids are never
    reused, even after deletion, so stale references remain visibly
    stale instead of silently aliasing a new node.
    """

    def __init__(self) -> None:
        self._nodes: dict[int, Node] = {}
        self._edges: list[Edge] = []
        self._max_id: int = 0

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.

        Replaces any existing node with the same id.

        Args:
            node: The node to add.
        """
        self._nodes[node.id] = node
        self._max_id = max(self._max_id, node.id)

    def remove_node(self, node_id: int) -> None:
        """Remove a node and all edges incident to it.

        The maximum assigned id is not decreased, so the id is never
        reused by next_id.

        Args:
            node_id: Identifier of the node to remove.

        Raises:
            KeyError: If the node does not exist.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} does not exist")
        del self._nodes[node_id]
        self._edges = [e for e in self._edges if not e.connects(node_id)]

    def has_node(self, node_id: int) -> bool:
        """Return True if a node with the given id exists.

        Args:
            node_id: Identifier of the node to check.

        Returns:
            True if the node exists in the graph.
        """
        return node_id in self._nodes

    def node(self, node_id: int) -> Node:
        """Return the node with the given id.

        Args:
            node_id: Identifier of the node to retrieve.

        Returns:
            The node with the given id.

        Raises:
            KeyError: If the node does not exist.
        """
        return self._nodes[node_id]

    def nodes(self) -> list[Node]:
        """Return a list of all nodes, in insertion order.

        Returns:
            A list of all nodes in the graph.
        """
        return list(self._nodes.values())

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph.

        Returns:
            The number of nodes.
        """
        return len(self._nodes)

    def next_id(self) -> int:
        """Return an unused node id.

        The id is always greater than every id ever assigned, so it is
        never reused, even after deletions.

        Returns:
            A positive integer not yet used as a node id.
        """
        return self._max_id + 1

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph.

        Args:
            edge: The edge to add.

        Raises:
            ValueError: If either endpoint does not exist.
        """
        if not self.has_node(edge.source):
            raise ValueError(f"Source node {edge.source} does not exist")
        if not self.has_node(edge.target):
            raise ValueError(f"Target node {edge.target} does not exist")
        self._edges.append(edge)

    def remove_edge(self, source: int, target: int) -> None:
        """Remove the first edge between two nodes.

        For undirected edges, the order of source and target does not matter.

        Args:
            source: Identifier of one endpoint.
            target: Identifier of the other endpoint.

        Raises:
            KeyError: If no matching edge exists.
        """
        for index, edge in enumerate(self._edges):
            if edge.source == source and edge.target == target:
                del self._edges[index]
                return
            if not edge.directed and edge.source == target and edge.target == source:
                del self._edges[index]
                return
        raise KeyError(f"Edge {source} -> {target} does not exist")

    def edges(self) -> list[Edge]:
        """Return a list of all edges, in insertion order.

        Returns:
            A list of all edges in the graph.
        """
        return list(self._edges)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph.

        Returns:
            The number of edges.
        """
        return len(self._edges)

    def neighbors(self, node_id: int) -> list[int]:
        """Return ids of all nodes adjacent to the given node.

        For undirected graphs, an edge is traversed in both directions.
        For directed graphs, only edges leaving the node are considered.
        Parallel edges are collapsed into a single entry.

        Args:
            node_id: Identifier of the node to query.

        Returns:
            A list of neighbouring node identifiers.

        Raises:
            KeyError: If the node does not exist.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} does not exist")

        seen: set[int] = set()
        result: list[int] = []
        for edge in self._edges:
            neighbor: int | None = None
            if edge.source == node_id:
                neighbor = edge.target
            elif not edge.directed and edge.target == node_id:
                neighbor = edge.source
            if neighbor is not None and neighbor not in seen:
                seen.add(neighbor)
                result.append(neighbor)
        return result
