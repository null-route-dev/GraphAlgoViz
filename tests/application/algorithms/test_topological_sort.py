"""Tests for the topological sort algorithm."""

import pytest

from application.algorithms.step_result import StepResult
from application.algorithms.topological_sort import TopologicalSort
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return a directed chain 1 -> 2 -> 3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    return graph


def build_diamond() -> Graph:
    """Return a directed diamond: 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=1, target=3, directed=True))
    graph.add_edge(Edge(source=2, target=4, directed=True))
    graph.add_edge(Edge(source=3, target=4, directed=True))
    return graph


def build_cycle() -> Graph:
    """Return a directed cycle 1 -> 2 -> 3 -> 1."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    graph.add_edge(Edge(source=3, target=1, directed=True))
    return graph


def run_to_completion(algorithm: TopologicalSort) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        TopologicalSort(graph, start_node_id=42)


def test_single_node_produces_one_step() -> None:
    """A graph with one node produces a single step."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = TopologicalSort(graph, start_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert result.labels == {1: "1"}
    assert algorithm.is_finished is True


def test_chain_is_sorted_in_order() -> None:
    """A directed chain is sorted from source to sink."""
    steps = run_to_completion(TopologicalSort(build_chain(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "1", 2: "2", 3: "3"}


def test_diamond_respects_dependencies() -> None:
    """Every edge goes from an earlier position to a later one."""
    steps = run_to_completion(TopologicalSort(build_diamond(), start_node_id=1))
    final = steps[-1]

    positions = {int(node): int(pos) for node, pos in final.labels.items()}
    assert positions[1] < positions[2]
    assert positions[1] < positions[3]
    assert positions[2] < positions[4]
    assert positions[3] < positions[4]


def test_first_node_has_no_incoming_edges() -> None:
    """The first node in the order has no incoming directed edges."""
    algorithm = TopologicalSort(build_diamond(), start_node_id=1)
    first = algorithm.step()

    assert first.current == 1
    assert first.frontier == (2, 3)


def test_cycle_leaves_nodes_unsorted() -> None:
    """A graph with a cycle cannot be fully sorted."""
    algorithm = TopologicalSort(build_cycle(), start_node_id=1)

    assert algorithm.is_finished is True


def test_cycle_reported_in_info() -> None:
    """The last step reports a cycle when nodes are left unsorted."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    graph.add_edge(Edge(source=3, target=2, directed=True))

    steps = run_to_completion(TopologicalSort(graph, start_node_id=1))
    final = steps[-1]

    assert "cycle detected" in final.info
    assert final.visited == frozenset({1, 2, 3}) or "unsorted" in final.info


def test_undirected_edges_are_ignored() -> None:
    """An undirected edge does not affect the sort order."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, directed=False))

    steps = run_to_completion(TopologicalSort(graph, start_node_id=1))

    assert len(steps) == 2
    assert steps[0].current == 1
    assert steps[1].current == 2


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = TopologicalSort(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_mentions_position() -> None:
    """Each step reports the position of the node in the order."""
    algorithm = TopologicalSort(build_chain(), start_node_id=1)
    result = algorithm.step()

    assert result.info == "Sorted node 1 (position 1)"
