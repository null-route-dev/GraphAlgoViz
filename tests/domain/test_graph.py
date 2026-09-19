"""Tests for the Graph aggregate."""

import pytest

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


@pytest.fixture
def empty_graph() -> Graph:
    """Return an empty graph."""
    return Graph()


@pytest.fixture
def graph_with_two_nodes() -> Graph:
    """Return a graph containing two nodes with ids 1 and 2."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A"))
    graph.add_node(Node(id=2, label="B"))
    return graph


def test_new_graph_is_empty(empty_graph: Graph) -> None:
    """A freshly created graph has no nodes and no edges."""
    assert empty_graph.node_count == 0
    assert empty_graph.edge_count == 0


def test_add_node(empty_graph: Graph) -> None:
    """add_node stores the node and updates the node count."""
    empty_graph.add_node(Node(id=1, label="A"))
    assert empty_graph.node_count == 1
    assert empty_graph.has_node(1) is True


def test_add_node_replaces_existing(empty_graph: Graph) -> None:
    """Adding a node with an existing id replaces the previous one."""
    empty_graph.add_node(Node(id=1, label="A"))
    empty_graph.add_node(Node(id=1, label="B"))
    assert empty_graph.node_count == 1
    assert empty_graph.node(1).label == "B"


def test_has_node_returns_false_for_missing(empty_graph: Graph) -> None:
    """has_node returns False for an id that was never added."""
    assert empty_graph.has_node(42) is False


def test_node_returns_stored_node(graph_with_two_nodes: Graph) -> None:
    """node returns the node with the given id."""
    assert graph_with_two_nodes.node(1).label == "A"


def test_node_raises_for_missing(empty_graph: Graph) -> None:
    """node raises KeyError for an unknown id."""
    with pytest.raises(KeyError):
        empty_graph.node(42)


def test_nodes_returns_all_in_insertion_order(graph_with_two_nodes: Graph) -> None:
    """nodes returns every stored node in insertion order."""
    assert [node.id for node in graph_with_two_nodes.nodes()] == [1, 2]


def test_remove_node(graph_with_two_nodes: Graph) -> None:
    """remove_node deletes the node and updates the count."""
    graph_with_two_nodes.remove_node(1)
    assert graph_with_two_nodes.node_count == 1
    assert graph_with_two_nodes.has_node(1) is False


def test_remove_node_raises_for_missing(empty_graph: Graph) -> None:
    """remove_node raises KeyError when the node does not exist."""
    with pytest.raises(KeyError):
        empty_graph.remove_node(42)


def test_remove_node_removes_incident_edges(graph_with_two_nodes: Graph) -> None:
    """Removing a node also removes every edge incident to it."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2))
    graph_with_two_nodes.remove_node(1)
    assert graph_with_two_nodes.edge_count == 0


def test_add_edge(graph_with_two_nodes: Graph) -> None:
    """add_edge stores the edge and updates the edge count."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2))
    assert graph_with_two_nodes.edge_count == 1


def test_add_edge_raises_for_missing_source(graph_with_two_nodes: Graph) -> None:
    """add_edge raises ValueError when the source node does not exist."""
    with pytest.raises(ValueError, match="Source node 42"):
        graph_with_two_nodes.add_edge(Edge(source=42, target=2))


def test_add_edge_raises_for_missing_target(graph_with_two_nodes: Graph) -> None:
    """add_edge raises ValueError when the target node does not exist."""
    with pytest.raises(ValueError, match="Target node 42"):
        graph_with_two_nodes.add_edge(Edge(source=1, target=42))


def test_remove_edge(graph_with_two_nodes: Graph) -> None:
    """remove_edge deletes an existing edge."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2))
    graph_with_two_nodes.remove_edge(1, 2)
    assert graph_with_two_nodes.edge_count == 0


def test_remove_edge_undirected_reverse_order(graph_with_two_nodes: Graph) -> None:
    """remove_edge handles an undirected edge given in reverse order."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2))
    graph_with_two_nodes.remove_edge(2, 1)
    assert graph_with_two_nodes.edge_count == 0


def test_remove_edge_raises_for_missing(graph_with_two_nodes: Graph) -> None:
    """remove_edge raises KeyError when no matching edge exists."""
    with pytest.raises(KeyError):
        graph_with_two_nodes.remove_edge(1, 2)


def test_edges_returns_all_in_insertion_order(graph_with_two_nodes: Graph) -> None:
    """edges returns every stored edge in insertion order."""
    first = Edge(source=1, target=2, weight=2.0)
    second = Edge(source=2, target=1, weight=3.0)
    graph_with_two_nodes.add_edge(first)
    graph_with_two_nodes.add_edge(second)
    assert graph_with_two_nodes.edges() == [first, second]


def test_neighbors_undirected(graph_with_two_nodes: Graph) -> None:
    """neighbors returns adjacent nodes for an undirected edge."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2))
    assert graph_with_two_nodes.neighbors(1) == [2]
    assert graph_with_two_nodes.neighbors(2) == [1]


def test_neighbors_directed(graph_with_two_nodes: Graph) -> None:
    """neighbors follows only outgoing edges for a directed edge."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2, directed=True))
    assert graph_with_two_nodes.neighbors(1) == [2]
    assert graph_with_two_nodes.neighbors(2) == []


def test_neighbors_collapses_parallel_edges(graph_with_two_nodes: Graph) -> None:
    """neighbors reports each adjacent node only once."""
    graph_with_two_nodes.add_edge(Edge(source=1, target=2, weight=1.0))
    graph_with_two_nodes.add_edge(Edge(source=1, target=2, weight=5.0))
    assert graph_with_two_nodes.neighbors(1) == [2]


def test_neighbors_raises_for_missing_node(empty_graph: Graph) -> None:
    """neighbors raises KeyError for an unknown node."""
    with pytest.raises(KeyError):
        empty_graph.neighbors(42)
