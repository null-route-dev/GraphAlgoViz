"""Tests for the Bellman-Ford shortest-path algorithm."""

import pytest

from application.algorithms.bellman_ford import BellmanFord
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return an undirected chain 1-2-3 with weights 1 and 2."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=2.0))
    return graph


def build_negative_dag() -> Graph:
    """Return a directed DAG with one negative edge."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=-5.0, directed=True))
    return graph


def build_negative_cycle() -> Graph:
    """Return a directed triangle with a negative cycle."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=-1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=-1.0, directed=True))
    graph.add_edge(Edge(source=3, target=1, weight=-1.0, directed=True))
    return graph


def build_detour() -> Graph:
    """Return a directed graph where the direct edge is worse."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=3, weight=10.0, directed=True))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=1.0, directed=True))
    return graph


def run_to_completion(algorithm: BellmanFord) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        BellmanFord(graph, start_node_id=42)


def test_single_node_finishes_immediately() -> None:
    """A graph with one node has nothing to relax."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = BellmanFord(graph, start_node_id=1)

    assert algorithm.is_finished is True
    assert algorithm.distances == {1: 0.0}


def test_two_nodes_without_edges_finishes_immediately() -> None:
    """A graph without edges needs no relaxation."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = BellmanFord(graph, start_node_id=1)

    assert algorithm.is_finished is True
    assert algorithm.distances == {1: 0.0}


def test_chain_distances() -> None:
    """A chain yields cumulative distances along the path."""
    algorithm = BellmanFord(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distances == {1: 0.0, 2: 1.0, 3: 3.0}


def test_negative_edge_is_relaxed() -> None:
    """A negative edge produces a smaller distance."""
    algorithm = BellmanFord(build_negative_dag(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distances == {1: 0.0, 2: 1.0, 3: -4.0}


def test_detour_is_preferred() -> None:
    """Node 3 is reached through node 2, not the heavy direct edge."""
    algorithm = BellmanFord(build_detour(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distances == {1: 0.0, 2: 1.0, 3: 2.0}


def test_unreachable_nodes_are_absent() -> None:
    """Nodes in a separate component never appear in distances."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = BellmanFord(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distances == {1: 0.0}
    assert algorithm.has_negative_cycle is False


def test_negative_cycle_is_detected() -> None:
    """A reachable negative cycle is reported."""
    algorithm = BellmanFord(build_negative_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.has_negative_cycle is True
    assert algorithm.is_finished is True


def test_no_negative_cycle_in_dag() -> None:
    """A DAG has no negative cycle."""
    algorithm = BellmanFord(build_negative_dag(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.has_negative_cycle is False


def test_undirected_negative_edge_forms_cycle() -> None:
    """An undirected negative edge is a cycle of length two."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=-1.0, directed=False))

    algorithm = BellmanFord(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.has_negative_cycle is True


def test_parallel_edges_use_minimum_for_distance() -> None:
    """Parallel edges contribute their shortest alternative."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0, directed=True))
    graph.add_edge(Edge(source=1, target=2, weight=2.0, directed=True))

    algorithm = BellmanFord(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distances == {1: 0.0, 2: 2.0}


def test_convergence_is_reported_in_info() -> None:
    """The last step of a converging run mentions convergence."""
    algorithm = BellmanFord(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "converged" in steps[-1].info


def test_negative_cycle_is_reported_in_info() -> None:
    """The last step of a negative-cycle run mentions the cycle."""
    algorithm = BellmanFord(build_negative_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "negative cycle detected" in steps[-1].info


def test_info_mentions_edge_and_pass() -> None:
    """Each step mentions the edge and the current pass."""
    algorithm = BellmanFord(build_chain(), start_node_id=1)
    result = algorithm.step()

    assert "Pass 1" in result.info
    assert "edge" in result.info


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = BellmanFord(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
