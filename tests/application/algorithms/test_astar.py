"""Tests for the A* shortest-path algorithm."""

import pytest

from application.algorithms.astar import AStar
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


def build_branching() -> Graph:
    """Return a graph with a path to target and a dead-end branch.

    Nodes 3 and 4 form a dead-end branch. The target 5 is only
    reachable through node 2. A* should not expand the dead-end
    nodes because their heuristic is high.
    """
    graph = Graph()
    for node_id in (1, 2, 3, 4, 5):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=5, weight=1.0))
    graph.add_edge(Edge(source=1, target=3, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=1.0))
    return graph


def run_to_completion(algorithm: AStar) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        AStar(graph, start_node_id=42, target_node_id=3)


def test_target_node_must_exist() -> None:
    """A missing target node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Target node 42"):
        AStar(graph, start_node_id=1, target_node_id=42)


def test_start_equals_target() -> None:
    """If start and target are the same, A* finishes in one step."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert algorithm.is_finished is True
    assert algorithm.target_reached is True
    assert algorithm.distance_to_target == 0.0


def test_chain_finds_target() -> None:
    """A* finds the shortest path along a chain."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    run_to_completion(algorithm)

    assert algorithm.target_reached is True
    assert algorithm.distance_to_target == 3.0


def test_branching_stops_early() -> None:
    """A* does not expand the dead-end branch when the target is elsewhere."""
    algorithm = AStar(build_branching(), start_node_id=1, target_node_id=5)
    steps = run_to_completion(algorithm)

    assert len(steps) == 3
    assert algorithm.target_reached is True
    assert algorithm.distance_to_target == 2.0


def test_branching_never_finalizes_dead_end() -> None:
    """Nodes 3 and 4 are never finalized because the target is reached first."""
    algorithm = AStar(build_branching(), start_node_id=1, target_node_id=5)
    steps = run_to_completion(algorithm)

    final = steps[-1]
    assert 3 not in final.visited
    assert 4 not in final.visited


def test_unreachable_target_finishes() -> None:
    """An unreachable target produces a final step without reaching it."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = AStar(graph, start_node_id=1, target_node_id=2)
    steps = run_to_completion(algorithm)

    assert algorithm.is_finished is True
    assert algorithm.target_reached is False
    assert "unreachable" in steps[-1].info


def test_distance_to_target_is_none_when_unreachable() -> None:
    """distance_to_target returns None when the target was not reached."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = AStar(graph, start_node_id=1, target_node_id=2)
    run_to_completion(algorithm)

    assert algorithm.distance_to_target is None


def test_directed_edges_are_respected() -> None:
    """A directed edge in the wrong direction is not traversed."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=3, target=2, weight=1.0, directed=True))

    algorithm = AStar(graph, start_node_id=1, target_node_id=3)
    run_to_completion(algorithm)

    assert algorithm.target_reached is False


def test_info_reports_g_h_f() -> None:
    """Each expansion step mentions g, h, and f."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    first = algorithm.step()

    assert "g=" in first.info
    assert "h=" in first.info
    assert "f=" in first.info


def test_initial_step_expands_start() -> None:
    """The first step expands the start node."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    first = algorithm.step()

    assert first.current == 1


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_labels_include_reached_nodes() -> None:
    """Every node with a known tentative distance appears in labels."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    first = algorithm.step()

    assert first.labels == {1: "0", 2: "1"}


def test_labels_after_first_step_exclude_unreached_neighbors() -> None:
    """Nodes not yet reached do not appear in labels."""
    algorithm = AStar(build_chain(), start_node_id=1, target_node_id=3)
    first = algorithm.step()

    assert 3 not in first.labels


def test_heuristic_is_zero_at_target() -> None:
    """The heuristic at the target is zero."""
    graph = build_chain()
    heuristic = AStar._compute_heuristic(graph, target_id=3)

    assert heuristic[3] == 0.0


def test_heuristic_uses_minimum_edge_weight() -> None:
    """The heuristic is hop count times the smallest edge weight."""
    graph = build_chain()
    heuristic = AStar._compute_heuristic(graph, target_id=3)

    assert heuristic[1] == pytest.approx(2.0)
    assert heuristic[2] == pytest.approx(1.0)
