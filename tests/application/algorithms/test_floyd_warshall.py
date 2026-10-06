"""Tests for the Floyd-Warshall all-pairs shortest-path algorithm."""

import pytest

from application.algorithms.floyd_warshall import (
    INFINITY_LABEL,
    FloydWarshall,
)
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_triangle() -> Graph:
    """Return a directed triangle 1->2->3->1 with distinct weights."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=2.0, directed=True))
    graph.add_edge(Edge(source=1, target=3, weight=10.0, directed=True))
    return graph


def build_detour() -> Graph:
    """Return a graph where the direct edge is heavier than a detour."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=3, weight=10.0, directed=True))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=1.0, directed=True))
    return graph


def run_to_completion(algorithm: FloydWarshall) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_triangle()
    with pytest.raises(ValueError, match="Start node 42"):
        FloydWarshall(graph, start_node_id=42)


def test_single_node_finishes_in_one_step() -> None:
    """A graph with one node produces a single step."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = FloydWarshall(graph, start_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert result.highlight_cell == (1, 1)
    assert algorithm.is_finished is True


def test_step_count_is_cubic() -> None:
    """The number of steps equals V^3."""
    graph = build_triangle()
    steps = run_to_completion(FloydWarshall(graph, start_node_id=1))

    assert len(steps) == 27


def test_detour_is_used() -> None:
    """The shortest path to node 3 goes through node 2."""
    algorithm = FloydWarshall(build_detour(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 3) == 2.0
    assert algorithm.distance(1, 2) == 1.0
    assert algorithm.distance(2, 3) == 1.0


def test_triangle_distances() -> None:
    """Every pair of nodes has a shortest distance."""
    algorithm = FloydWarshall(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 1) == 0.0
    assert algorithm.distance(1, 2) == 1.0
    assert algorithm.distance(1, 3) == 3.0
    assert algorithm.distance(2, 3) == 2.0


def test_unreachable_pair_is_none() -> None:
    """Nodes in separate components have no distance between them."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))

    algorithm = FloydWarshall(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 2) == 1.0
    assert algorithm.distance(1, 3) is None
    assert algorithm.distance(2, 3) is None


def test_matrix_uses_infinity_for_unreachable_pairs() -> None:
    """The matrix shows infinity for unreachable pairs."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = FloydWarshall(graph, start_node_id=1)
    result = algorithm.step()

    assert result.matrix[(1, 2)] == INFINITY_LABEL
    assert result.matrix[(2, 1)] == INFINITY_LABEL


def test_matrix_has_self_distances() -> None:
    """The diagonal of the matrix contains zeros."""
    graph = build_triangle()
    algorithm = FloydWarshall(graph, start_node_id=1)
    result = algorithm.step()

    assert result.matrix[(1, 1)] == "0"
    assert result.matrix[(2, 2)] == "0"
    assert result.matrix[(3, 3)] == "0"


def test_matrix_covers_all_pairs() -> None:
    """Every ordered pair of nodes has a matrix entry."""
    graph = build_triangle()
    algorithm = FloydWarshall(graph, start_node_id=1)
    result = algorithm.step()

    assert len(result.matrix) == 9
    for i in (1, 2, 3):
        for j in (1, 2, 3):
            assert (i, j) in result.matrix


def test_highlight_cell_advances_through_pairs() -> None:
    """The highlighted cell moves through every (i, j) pair for each k."""
    graph = build_triangle()
    algorithm = FloydWarshall(graph, start_node_id=1)

    seen: list[tuple[int, int]] = []
    first_k = None
    for _ in range(9):
        result = algorithm.step()
        if first_k is None:
            first_k = result.current
        if result.current != first_k:
            break
        assert result.highlight_cell is not None
        seen.append(result.highlight_cell)

    assert seen == [
        (1, 1),
        (1, 2),
        (1, 3),
        (2, 1),
        (2, 2),
        (2, 3),
        (3, 1),
        (3, 2),
        (3, 3),
    ]


def test_undirected_edges_are_symmetric() -> None:
    """An undirected edge produces symmetric distances."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=3.0, directed=False))

    algorithm = FloydWarshall(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 2) == 3.0
    assert algorithm.distance(2, 1) == 3.0


def test_negative_edge_is_used() -> None:
    """A negative edge reduces the shortest distance."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=-5.0, directed=True))

    algorithm = FloydWarshall(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 3) == -4.0


def test_parallel_edges_use_minimum_weight() -> None:
    """Initial distances use the minimum weight among parallel edges."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0, directed=True))
    graph.add_edge(Edge(source=1, target=2, weight=2.0, directed=True))

    algorithm = FloydWarshall(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.distance(1, 2) == 2.0


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = FloydWarshall(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_mentions_k_and_pair() -> None:
    """Each step mentions the intermediate node and the pair."""
    algorithm = FloydWarshall(build_triangle(), start_node_id=1)
    result = algorithm.step()

    assert "k=1" in result.info
    assert "d[1][1]" in result.info


def test_visited_grows_with_k_progress() -> None:
    """Nodes are added to visited as k passes complete."""
    graph = build_triangle()
    algorithm = FloydWarshall(graph, start_node_id=1)

    first = algorithm.step()
    assert first.visited == frozenset()
    assert first.current == 1
