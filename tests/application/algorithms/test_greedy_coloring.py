"""Tests for the greedy graph coloring algorithm."""

import pytest

from application.algorithms.greedy_coloring import GreedyColoring
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return a chain 1-2-3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    return graph


def build_triangle() -> Graph:
    """Return a triangle of three mutually connected nodes."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=1, target=3))
    return graph


def build_star() -> Graph:
    """Return a star with node 1 at the center."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))
    graph.add_edge(Edge(source=1, target=4))
    return graph


def run_to_completion(algorithm: GreedyColoring) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        GreedyColoring(graph, start_node_id=42)


def test_single_node_gets_first_color() -> None:
    """A graph with one node colors it with color 1."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = GreedyColoring(graph, start_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert result.labels == {1: "1"}
    assert algorithm.is_finished is True


def test_chain_uses_two_colors() -> None:
    """A chain alternates between two colors."""
    steps = run_to_completion(GreedyColoring(build_chain(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "1", 2: "2", 3: "1"}


def test_triangle_uses_three_colors() -> None:
    """A triangle requires three distinct colors."""
    steps = run_to_completion(GreedyColoring(build_triangle(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "1", 2: "2", 3: "3"}


def test_star_uses_two_colors() -> None:
    """A star colors the center with 1 and every leaf with 2."""
    steps = run_to_completion(GreedyColoring(build_star(), start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "1", 2: "2", 3: "2", 4: "2"}


def test_each_step_colors_exactly_one_node() -> None:
    """The number of steps equals the number of nodes."""
    steps = run_to_completion(GreedyColoring(build_star(), start_node_id=1))

    assert len(steps) == 4


def test_frontier_shrinks_by_one_each_step() -> None:
    """Frontier holds the nodes not yet colored."""
    algorithm = GreedyColoring(build_chain(), start_node_id=1)
    first = algorithm.step()

    assert first.frontier == (2, 3)


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = GreedyColoring(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_mentions_node_and_color() -> None:
    """Each step describes which node received which color."""
    algorithm = GreedyColoring(build_chain(), start_node_id=1)
    result = algorithm.step()

    assert result.info == "Colored node 1 with color 1"


def test_isolated_node_gets_first_color() -> None:
    """A node without neighbors always receives color 1."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    steps = run_to_completion(GreedyColoring(graph, start_node_id=1))
    final = steps[-1]

    assert final.labels == {1: "1", 2: "1"}
