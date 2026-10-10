"""Tests for the bipartite check algorithm."""

import pytest

from application.algorithms.bipartite_check import (
    COLOR_A,
    COLOR_B,
    BipartiteCheck,
)
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_even_cycle() -> Graph:
    """Return an undirected 4-cycle 1-2-3-4-1."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=4))
    graph.add_edge(Edge(source=4, target=1))
    return graph


def build_odd_cycle() -> Graph:
    """Return an undirected 3-cycle (triangle)."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=1))
    return graph


def build_star() -> Graph:
    """Return an undirected star centered at node 1."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))
    graph.add_edge(Edge(source=1, target=4))
    return graph


def build_chain() -> Graph:
    """Return an undirected chain 1-2-3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    return graph


def build_two_components_bipartite() -> Graph:
    """Return two disconnected components, both bipartite."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))
    return graph


def build_two_components_one_odd() -> Graph:
    """Return a bipartite pair plus a triangle."""
    graph = Graph()
    for node_id in (1, 2, 3, 4, 5):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))
    graph.add_edge(Edge(source=4, target=5))
    graph.add_edge(Edge(source=5, target=3))
    return graph


def run_to_completion(algorithm: BipartiteCheck) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        BipartiteCheck(graph, start_node_id=42)


def test_single_node_is_bipartite() -> None:
    """A single node is trivially bipartite."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_single_edge_is_bipartite() -> None:
    """Two nodes connected by an edge are bipartite."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_chain_is_bipartite() -> None:
    """A chain is always bipartite."""
    algorithm = BipartiteCheck(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_even_cycle_is_bipartite() -> None:
    """An even cycle is bipartite."""
    algorithm = BipartiteCheck(build_even_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_star_is_bipartite() -> None:
    """A star is bipartite: center in one set, all leaves in the other."""
    algorithm = BipartiteCheck(build_star(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_odd_cycle_is_not_bipartite() -> None:
    """A triangle is not bipartite."""
    algorithm = BipartiteCheck(build_odd_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is False


def test_conflict_edge_is_reported() -> None:
    """The edge that broke bipartiteness is available after the run."""
    algorithm = BipartiteCheck(build_odd_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.conflict_edge is not None
    a, b = algorithm.conflict_edge
    assert {a, b}.issubset({1, 2, 3})


def test_two_components_all_bipartite() -> None:
    """A graph whose components are all bipartite is bipartite."""
    algorithm = BipartiteCheck(build_two_components_bipartite(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_two_components_one_odd_is_not_bipartite() -> None:
    """One non-bipartite component makes the whole graph non-bipartite."""
    algorithm = BipartiteCheck(build_two_components_one_odd(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is False


def test_colors_use_the_two_declared_values() -> None:
    """Every node receives one of the two palette colors."""
    algorithm = BipartiteCheck(build_even_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)
    colors = steps[-1].node_colors

    for color in colors.values():
        assert color in (COLOR_A, COLOR_B)


def test_adjacent_nodes_have_different_colors() -> None:
    """In a bipartite graph, every edge joins nodes of different colors."""
    graph = build_even_cycle()
    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    for edge in graph.edges():
        assert algorithm.color_of(edge.source) != algorithm.color_of(edge.target)


def test_star_center_color_differs_from_leaves() -> None:
    """The center of a star has the opposite color from all leaves."""
    algorithm = BipartiteCheck(build_star(), start_node_id=1)
    run_to_completion(algorithm)

    center = algorithm.color_of(1)
    for leaf in (2, 3, 4):
        assert algorithm.color_of(leaf) != center


def test_color_of_unvisited_node_is_none() -> None:
    """Before the algorithm reaches a node, its color is None."""
    algorithm = BipartiteCheck(build_chain(), start_node_id=1)

    assert algorithm.color_of(3) is None


def test_info_reports_conflict() -> None:
    """The final step of a non-bipartite graph mentions the conflict."""
    algorithm = BipartiteCheck(build_odd_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "Conflict" in steps[-1].info


def test_info_reports_bipartite_when_done() -> None:
    """The final step of a bipartite graph says so."""
    algorithm = BipartiteCheck(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "bipartite" in steps[-1].info


def test_directed_edges_are_treated_as_undirected() -> None:
    """Direction does not matter for bipartiteness."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, directed=True))

    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_directed_odd_cycle_is_not_bipartite() -> None:
    """A directed triangle is still not bipartite."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    graph.add_edge(Edge(source=3, target=1, directed=True))

    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is False


def test_parallel_edges_do_not_break_bipartite() -> None:
    """Two parallel edges between the same nodes are still bipartite."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BipartiteCheck(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.is_bipartite is True


def test_conflict_edge_appears_in_tree_edges() -> None:
    """The conflict edge is highlighted in the step that detects it."""
    algorithm = BipartiteCheck(build_odd_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)
    final = steps[-1]

    assert final.tree_edges == frozenset({algorithm.conflict_edge})


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = BipartiteCheck(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
