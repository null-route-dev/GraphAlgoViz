"""Tests for the graph statistics module."""

import pytest

from application.statistics import (
    DEFAULT_MAX_NODES_FOR_PATHS,
    compute_statistics,
)
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def _chain(length: int) -> Graph:
    graph = Graph()
    for i in range(1, length + 1):
        graph.add_node(Node(id=i))
    for i in range(1, length):
        graph.add_edge(Edge(source=i, target=i + 1))
    return graph


def _cycle(length: int) -> Graph:
    graph = Graph()
    for i in range(1, length + 1):
        graph.add_node(Node(id=i))
    for i in range(1, length):
        graph.add_edge(Edge(source=i, target=i + 1))
    graph.add_edge(Edge(source=length, target=1))
    return graph


def test_empty_graph() -> None:
    """An empty graph reports zeros and no path metrics."""
    stats = compute_statistics(Graph())

    assert stats.node_count == 0
    assert stats.edge_count == 0
    assert stats.density == 0.0
    assert stats.average_degree == 0.0
    assert stats.component_count == 0
    assert stats.diameter is None
    assert stats.average_path_length is None


def test_single_node() -> None:
    """A single-node graph has zero distances by convention."""
    graph = Graph()
    graph.add_node(Node(id=1))

    stats = compute_statistics(graph)

    assert stats.node_count == 1
    assert stats.edge_count == 0
    assert stats.density == 0.0
    assert stats.average_degree == 0.0
    assert stats.component_count == 1
    assert stats.diameter == 0
    assert stats.average_path_length == 0.0


def test_single_edge() -> None:
    """Two nodes joined by one edge form a connected graph."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))

    stats = compute_statistics(graph)

    assert stats.node_count == 2
    assert stats.edge_count == 1
    assert stats.density == 1.0
    assert stats.average_degree == 1.0
    assert stats.component_count == 1
    assert stats.diameter == 1
    assert stats.average_path_length == 1.0


def test_chain_diameter_and_average_path() -> None:
    """A chain of five nodes has diameter 4 and mean path 2."""
    stats = compute_statistics(_chain(5))

    assert stats.diameter == 4
    assert stats.average_path_length == pytest.approx(2.0)


def test_cycle_path_metrics() -> None:
    """A 4-cycle has diameter 2 and mean path 4/3."""
    stats = compute_statistics(_cycle(4))

    assert stats.diameter == 2
    assert stats.average_path_length == pytest.approx(8 / 6)


def test_disconnected_graph_has_no_path_metrics() -> None:
    """Two disconnected edges give two components and no diameter."""
    graph = Graph()
    for i in (1, 2, 3, 4):
        graph.add_node(Node(id=i))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))

    stats = compute_statistics(graph)

    assert stats.component_count == 2
    assert stats.diameter is None
    assert stats.average_path_length is None


def test_isolated_nodes_count_as_components() -> None:
    """Each isolated node is its own component."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))

    stats = compute_statistics(graph)

    assert stats.component_count == 3


def test_self_loops_are_ignored_for_density() -> None:
    """Self-loops do not contribute to density or average degree."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_edge(Edge(source=1, target=1))

    stats = compute_statistics(graph)

    assert stats.node_count == 1
    assert stats.edge_count == 1
    assert stats.density == 0.0
    assert stats.average_degree == 0.0


def test_directed_edge_contributes_to_connectivity() -> None:
    """A directed edge is treated as undirected for connectivity."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, directed=True))

    stats = compute_statistics(graph)

    assert stats.component_count == 1
    assert stats.diameter == 1


def test_density_of_complete_graph() -> None:
    """A complete graph on four nodes has density 1 and degree 3."""
    graph = Graph()
    for i in (1, 2, 3, 4):
        graph.add_node(Node(id=i))
    for u in range(1, 5):
        for v in range(u + 1, 5):
            graph.add_edge(Edge(source=u, target=v))

    stats = compute_statistics(graph)

    assert stats.edge_count == 6
    assert stats.density == 1.0
    assert stats.average_degree == 3.0


def test_large_graph_skips_path_metrics() -> None:
    """Above the threshold, path metrics are None."""
    stats = compute_statistics(_chain(60), max_nodes_for_paths=50)

    assert stats.node_count == 60
    assert stats.diameter is None
    assert stats.average_path_length is None


def test_threshold_is_respected() -> None:
    """A chain above the threshold does not compute path metrics."""
    stats = compute_statistics(_chain(10), max_nodes_for_paths=5)

    assert stats.diameter is None


def test_default_threshold_constant() -> None:
    """The default threshold is fifty nodes."""
    assert DEFAULT_MAX_NODES_FOR_PATHS == 50
