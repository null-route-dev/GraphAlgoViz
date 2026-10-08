"""Tests for bridges and articulation points."""

import pytest

from application.algorithms.bridges_articulations import (
    ARTICULATION_COLOR,
    BridgesAndArticulations,
)
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain(length: int) -> Graph:
    """Return an undirected chain 1-2-...-length."""
    graph = Graph()
    for node_id in range(1, length + 1):
        graph.add_node(Node(id=node_id))
    for node_id in range(1, length):
        graph.add_edge(Edge(source=node_id, target=node_id + 1))
    return graph


def build_triangle() -> Graph:
    """Return an undirected triangle."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=1))
    return graph


def build_square() -> Graph:
    """Return an undirected square."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=4))
    graph.add_edge(Edge(source=4, target=1))
    return graph


def build_star() -> Graph:
    """Return an undirected star with node 1 in the center."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))
    graph.add_edge(Edge(source=1, target=4))
    return graph


def build_two_components() -> Graph:
    """Return two disconnected edges: 1-2 and 3-4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))
    return graph


def run_to_completion(algorithm: BridgesAndArticulations) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain(3)
    with pytest.raises(ValueError, match="Start node 42"):
        BridgesAndArticulations(graph, start_node_id=42)


def test_single_node_has_no_bridges_or_articulations() -> None:
    """A single node graph has neither bridges nor articulation points."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == []
    assert algorithm.articulation_points == []


def test_single_edge_is_a_bridge() -> None:
    """A graph of two nodes and one edge has exactly one bridge."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(1, 2)]
    assert algorithm.articulation_points == []


def test_chain_of_three() -> None:
    """A 3-chain has two bridges and one articulation point."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(1, 2), (2, 3)]
    assert algorithm.articulation_points == [2]


def test_chain_of_five() -> None:
    """A 5-chain has four bridges and three articulation points."""
    algorithm = BridgesAndArticulations(build_chain(5), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(1, 2), (2, 3), (3, 4), (4, 5)]
    assert algorithm.articulation_points == [2, 3, 4]


def test_triangle_has_no_bridges() -> None:
    """A triangle has neither bridges nor articulation points."""
    algorithm = BridgesAndArticulations(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == []
    assert algorithm.articulation_points == []


def test_square_has_no_bridges() -> None:
    """A square has neither bridges nor articulation points."""
    algorithm = BridgesAndArticulations(build_square(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == []
    assert algorithm.articulation_points == []


def test_star_center_is_articulation() -> None:
    """The center of a star is an articulation point, all edges are bridges."""
    algorithm = BridgesAndArticulations(build_star(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.articulation_points == [1]
    assert algorithm.bridges == [(1, 2), (1, 3), (1, 4)]


def test_two_components() -> None:
    """Every edge of two isolated edges is a bridge."""
    algorithm = BridgesAndArticulations(build_two_components(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(1, 2), (3, 4)]
    assert algorithm.articulation_points == []


def test_parallel_edges_are_not_a_bridge() -> None:
    """Two nodes connected by two parallel edges have no bridge."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == []


def test_parallel_edges_prevent_articulation() -> None:
    """Adding a second parallel edge to a bridge removes it from bridges."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(2, 3)]
    assert algorithm.articulation_points == [2]


def test_directed_edges_are_treated_as_undirected() -> None:
    """Directed edges participate in both directions."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, directed=True))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.bridges == [(1, 2)]


def test_lowlink_of_visited_node_is_reported() -> None:
    """The low-link of a visited node can be queried."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    algorithm.step()

    assert algorithm.lowlink_of(1) == 0


def test_lowlink_of_unvisited_node_is_none() -> None:
    """The low-link of an unvisited node is None."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)

    assert algorithm.lowlink_of(2) is None


def test_articulations_are_colored() -> None:
    """Articulation points receive the articulation color."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    steps = run_to_completion(algorithm)
    colors = steps[-1].node_colors

    assert colors[2] == ARTICULATION_COLOR
    assert 1 not in colors
    assert 3 not in colors


def test_bridges_are_reported_in_tree_edges() -> None:
    """Every bridge appears in tree_edges of the final snapshot."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert steps[-1].tree_edges == frozenset({(1, 2), (2, 3)})


def test_info_reports_bridge_finding() -> None:
    """The step that discovers a bridge mentions it."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    steps = run_to_completion(algorithm)
    messages = [step.info for step in steps]

    assert any("Bridge found" in msg for msg in messages)


def test_info_reports_articulation_finding() -> None:
    """The step that discovers an articulation point mentions it."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    steps = run_to_completion(algorithm)
    messages = [step.info for step in steps]

    assert any("Articulation point" in msg for msg in messages)


def test_root_with_two_children_is_articulation() -> None:
    """The DFS root with more than one child is an articulation point."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))

    algorithm = BridgesAndArticulations(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.articulation_points == [1]


def test_final_step_reports_counts() -> None:
    """The last step reports the total number of bridges and articulations."""
    algorithm = BridgesAndArticulations(build_chain(5), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "4 bridge" in steps[-1].info
    assert "3 articulation" in steps[-1].info


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = BridgesAndArticulations(build_chain(3), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_frontier_is_the_dfs_path() -> None:
    """Frontier contains the current DFS path from the root."""
    algorithm = BridgesAndArticulations(build_chain(4), start_node_id=1)
    algorithm.step()
    second = algorithm.step()

    assert second.frontier == (1, 2)
