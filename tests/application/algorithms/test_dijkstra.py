"""Tests for the Dijkstra shortest-path algorithm."""

import pytest

from application.algorithms.dijkstra import Dijkstra
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return a chain 1-2-3 with weights 1 and 2."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=2.0))
    return graph


def build_detour() -> Graph:
    """Return a graph where the direct edge is heavier than a detour."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=3, weight=10.0))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=1.0))
    return graph


def build_diamond() -> Graph:
    """Return a diamond with asymmetric paths to node 4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=1, target=3, weight=4.0))
    graph.add_edge(Edge(source=2, target=4, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=1.0))
    return graph


def run_to_completion(algorithm: Dijkstra) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        Dijkstra(graph, start_node_id=42)


def test_single_node_graph_finishes_in_one_step() -> None:
    """A graph with one node produces one step with distance 0."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = Dijkstra(graph, start_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert result.visited == frozenset({1})
    assert result.frontier == ()
    assert result.labels == {1: "0"}
    assert algorithm.is_finished is True


def test_chain_distances() -> None:
    """A chain yields cumulative distances along the path."""
    steps = run_to_completion(Dijkstra(build_chain(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0", 2: "1", 3: "3"}
    assert final.visited == frozenset({1, 2, 3})


def test_detour_is_preferred_over_direct_edge() -> None:
    """Node 3 is reached through node 2, not through the heavy direct edge."""
    steps = run_to_completion(Dijkstra(build_detour(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0", 2: "1", 3: "2"}
    assert (2, 3) in final.tree_edges
    assert (1, 3) not in final.tree_edges


def test_diamond_picks_shorter_path() -> None:
    """Node 4 is reached through the cheaper of two paths."""
    steps = run_to_completion(Dijkstra(build_diamond(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0", 2: "1", 4: "2", 3: "3"}
    assert (2, 4) in final.tree_edges
    assert (3, 4) not in final.tree_edges


def test_frontier_is_sorted_by_distance() -> None:
    """The frontier is ordered by tentative distance ascending."""
    algorithm = Dijkstra(build_diamond(), start_node_id=1)
    first = algorithm.step()

    assert first.frontier == (2, 3)


def test_labels_include_all_reached_nodes() -> None:
    """Every node with a tentative distance appears in labels."""
    algorithm = Dijkstra(build_diamond(), start_node_id=1)
    algorithm.step()

    assert set(algorithm.step().labels.keys()) == {1, 2, 3, 4}


def test_unreachable_nodes_are_absent() -> None:
    """Nodes in a separate component never appear in labels or visited."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    steps = run_to_completion(Dijkstra(graph, start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0"}
    assert final.visited == frozenset({1})


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = Dijkstra(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_is_human_readable() -> None:
    """Each step mentions the finalized node and its distance."""
    algorithm = Dijkstra(build_chain(), start_node_id=1)
    result = algorithm.step()

    assert result.info == "Finalized node 1 at distance 0"
