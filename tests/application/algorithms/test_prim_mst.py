"""Tests for Prim's minimum spanning tree algorithm."""

import pytest

from application.algorithms.prim_mst import PrimMST
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


def build_triangle() -> Graph:
    """Return a triangle with three edges of distinct weights."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=2.0))
    graph.add_edge(Edge(source=1, target=3, weight=5.0))
    return graph


def build_diamond() -> Graph:
    """Return a diamond with two cheap paths to node 4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=1, target=3, weight=10.0))
    graph.add_edge(Edge(source=2, target=4, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=1.0))
    return graph


def run_to_completion(algorithm: PrimMST) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        PrimMST(graph, start_node_id=42)


def test_single_node_graph_is_finished_immediately() -> None:
    """A graph with one node has an empty MST and finishes at once."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = PrimMST(graph, start_node_id=1)

    assert algorithm.is_finished is True


def test_isolated_start_node_is_finished_immediately() -> None:
    """An isolated start node produces no steps."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    graph.remove_edge(1, 2)

    algorithm = PrimMST(graph, start_node_id=1)

    assert algorithm.is_finished is True


def test_chain_includes_both_edges() -> None:
    """A chain's MST includes every edge of the chain."""
    algorithm = PrimMST(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert len(steps) == 2
    assert steps[-1].tree_edges == frozenset({(1, 2), (2, 3)})
    assert steps[-1].visited == frozenset({1, 2, 3})


def test_triangle_picks_cheapest_two_edges() -> None:
    """A triangle's MST excludes the heaviest edge."""
    steps = run_to_completion(PrimMST(build_triangle(), start_node_id=1))
    final = steps[-1]

    assert (1, 3) not in final.tree_edges
    assert (1, 2) in final.tree_edges
    assert (2, 3) in final.tree_edges


def test_triangle_total_weight() -> None:
    """The total weight of the MST is the sum of its edges."""
    steps = run_to_completion(PrimMST(build_triangle(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0", 2: "1", 3: "2"}


def test_diamond_total_weight() -> None:
    """A diamond's MST avoids the heavy direct edge to node 3."""
    steps = run_to_completion(PrimMST(build_diamond(), start_node_id=1))
    final = steps[-1]

    assert (1, 3) not in final.tree_edges
    assert final.labels == {1: "0", 2: "1", 3: "1", 4: "1"}


def test_parallel_edges_use_minimum_weight() -> None:
    """Parallel edges contribute only their minimum weight to the tree."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0))
    graph.add_edge(Edge(source=1, target=2, weight=2.0))

    steps = run_to_completion(PrimMST(graph, start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "0", 2: "2"}


def test_unreachable_nodes_are_absent() -> None:
    """Nodes outside the start component never enter the tree."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))
    graph.add_node(Node(id=4))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))

    steps = run_to_completion(PrimMST(graph, start_node_id=1))
    final = steps[-1]

    assert final.visited == frozenset({1, 2})
    assert final.tree_edges == frozenset({(1, 2)})


def test_current_is_the_added_node() -> None:
    """Each step sets current to the node just added to the tree."""
    algorithm = PrimMST(build_chain(), start_node_id=1)
    first = algorithm.step()

    assert first.current == 2
    assert first.visited == frozenset({1, 2})


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = PrimMST(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_is_human_readable() -> None:
    """Each step mentions the added node and the running total."""
    algorithm = PrimMST(build_triangle(), start_node_id=1)
    result = algorithm.step()

    assert result.info == "Added node 2 via edge weight 1, total 1"
