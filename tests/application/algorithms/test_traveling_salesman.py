"""Tests for the nearest-neighbor + 2-opt traveling salesman algorithm."""

import pytest

from application.algorithms.step_result import StepResult
from application.algorithms.traveling_salesman import TravelingSalesman
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_square_with_crossing() -> Graph:
    """Return a four-node graph where nearest neighbor produces a bad tour."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=1.0))
    graph.add_edge(Edge(source=4, target=1, weight=10.0))
    graph.add_edge(Edge(source=1, target=3, weight=1.0))
    graph.add_edge(Edge(source=2, target=4, weight=1.0))
    return graph


def build_triangle() -> Graph:
    """Return a complete triangle with all edges of weight 1."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=1.0))
    graph.add_edge(Edge(source=1, target=3, weight=1.0))
    return graph


def build_chain() -> Graph:
    """Return an undirected chain 1-2-3 with weights 1 and 1."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=1.0))
    return graph


def build_disconnected() -> Graph:
    """Return two isolated components: 1-2 and 3-4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=1.0))
    return graph


def run_to_completion(algorithm: TravelingSalesman) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_triangle()
    with pytest.raises(ValueError, match="Start node 42"):
        TravelingSalesman(graph, start_node_id=42)


def test_single_node_finishes_immediately() -> None:
    """A single-node graph has an empty tour and finishes at once."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = TravelingSalesman(graph, start_node_id=1)

    assert algorithm.is_finished is True


def test_two_nodes_close_the_tour() -> None:
    """Two connected nodes yield a tour of two edges."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=3.0))

    algorithm = TravelingSalesman(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert set(algorithm.tour()) == {1, 2}
    assert algorithm.tour_length() == pytest.approx(6.0)


def test_tour_visits_every_reachable_node() -> None:
    """Nearest neighbor visits every node in the connected component."""
    algorithm = TravelingSalesman(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    assert set(algorithm.tour()) == {1, 2, 3}


def test_triangle_tour_length() -> None:
    """A complete triangle with unit weights has tour length three."""
    algorithm = TravelingSalesman(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.tour_length() == pytest.approx(3.0)


def test_2opt_improves_a_crossing_tour() -> None:
    """2-opt replaces an expensive edge with two cheap ones."""
    algorithm = TravelingSalesman(build_square_with_crossing(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.tour_length() == pytest.approx(4.0)


def test_2opt_keeps_tour_valid() -> None:
    """After 2-opt, every consecutive pair of nodes is an edge."""
    graph = build_square_with_crossing()
    algorithm = TravelingSalesman(graph, start_node_id=1)
    run_to_completion(algorithm)

    tour = algorithm.tour()
    for i in range(len(tour)):
        u = tour[i]
        v = tour[(i + 1) % len(tour)]
        key = (min(u, v), max(u, v))
        has_edge = any(
            (min(e.source, e.target), max(e.source, e.target)) == key
            for e in graph.edges()
        )
        assert has_edge


def test_disconnected_graph_stops_early() -> None:
    """When no reachable neighbor remains, the tour covers only its component."""
    algorithm = TravelingSalesman(build_disconnected(), start_node_id=1)
    run_to_completion(algorithm)

    assert set(algorithm.tour()).issubset({1, 2})


def test_tour_length_grows_during_nearest_neighbor() -> None:
    """Each nearest-neighbor step increases the tour's edge count."""
    algorithm = TravelingSalesman(build_triangle(), start_node_id=1)
    edge_counts: list[int] = []
    while not algorithm.is_finished:
        step = algorithm.step()
        edge_counts.append(len(step.tree_edges))
    assert edge_counts == sorted(edge_counts)


def test_labels_number_the_tour_positions() -> None:
    """Each node in the tour receives a 1-based position label."""
    algorithm = TravelingSalesman(build_triangle(), start_node_id=1)
    steps = run_to_completion(algorithm)
    labels = steps[-1].labels

    assert labels[algorithm.tour()[0]] == "1"
    assert labels[algorithm.tour()[1]] == "2"
    assert labels[algorithm.tour()[2]] == "3"


def test_directed_edges_treated_as_undirected() -> None:
    """A directed edge is usable in either direction for a tour."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))

    algorithm = TravelingSalesman(graph, start_node_id=2)
    run_to_completion(algorithm)

    assert set(algorithm.tour()) == {1, 2}


def test_parallel_edges_use_minimum_weight() -> None:
    """The tour uses the lighter of two parallel edges."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0))
    graph.add_edge(Edge(source=1, target=2, weight=2.0))

    algorithm = TravelingSalesman(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.tour_length() == pytest.approx(4.0)


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = TravelingSalesman(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
