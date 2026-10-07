"""Tests for Kruskal's minimum spanning tree algorithm."""

import pytest

from application.algorithms.kruskal_mst import COMPONENT_PALETTE, KruskalMST
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return an undirected chain 1-2-3 with weights 2 and 1."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=2.0))
    graph.add_edge(Edge(source=2, target=3, weight=1.0))
    return graph


def build_triangle() -> Graph:
    """Return an undirected triangle with three distinct weights."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=2, target=3, weight=2.0))
    graph.add_edge(Edge(source=1, target=3, weight=5.0))
    return graph


def build_two_components() -> Graph:
    """Return a graph with two disconnected components."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=1.0))
    graph.add_edge(Edge(source=3, target=4, weight=2.0))
    return graph


def run_to_completion(algorithm: KruskalMST) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        KruskalMST(graph, start_node_id=42)


def test_single_node_has_no_edges() -> None:
    """A graph with one node finishes immediately."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = KruskalMST(graph, start_node_id=1)

    assert algorithm.is_finished is True
    assert algorithm.total_weight == 0.0


def test_chain_includes_both_edges() -> None:
    """A chain's MST includes both edges."""
    algorithm = KruskalMST(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert len(steps) == 2
    assert algorithm.total_weight == 3.0


def test_triangle_excludes_heaviest_edge() -> None:
    """A triangle's MST excludes the heaviest edge."""
    algorithm = KruskalMST(build_triangle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.total_weight == 3.0


def test_first_step_accepts_the_lightest_edge() -> None:
    """Edges are processed in weight order, so the lightest comes first."""
    algorithm = KruskalMST(build_triangle(), start_node_id=1)
    first = algorithm.step()

    assert first.current_edge == (1, 2)
    assert "Accepted" in first.info


def test_third_step_rejects_the_cycle_edge() -> None:
    """The heaviest edge of a triangle is rejected."""
    algorithm = KruskalMST(build_triangle(), start_node_id=1)
    algorithm.step()
    algorithm.step()
    third = algorithm.step()

    assert third.current_edge == (1, 3)
    assert "Rejected" in third.info


def test_tree_edges_accumulate_accepted_edges() -> None:
    """Every accepted edge appears in tree_edges."""
    algorithm = KruskalMST(build_triangle(), start_node_id=1)
    steps = run_to_completion(algorithm)

    final = steps[-1]
    assert final.tree_edges == frozenset({(1, 2), (2, 3)})


def test_components_get_distinct_colors() -> None:
    """Disconnected components receive different fill colors."""
    algorithm = KruskalMST(build_two_components(), start_node_id=1)
    steps = run_to_completion(algorithm)
    colors = steps[-1].node_colors

    assert colors[1] == colors[2]
    assert colors[3] == colors[4]
    assert colors[1] != colors[3]


def test_components_merge_to_one_color() -> None:
    """When a chain is fully spanned, all nodes share one color."""
    algorithm = KruskalMST(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)

    colors = steps[-1].node_colors
    assert colors[1] == colors[2] == colors[3]


def test_colors_come_from_palette() -> None:
    """Every component color is taken from the palette."""
    algorithm = KruskalMST(build_two_components(), start_node_id=1)
    steps = run_to_completion(algorithm)

    for color in steps[-1].node_colors.values():
        assert color in COMPONENT_PALETTE


def test_directed_edges_are_treated_as_undirected() -> None:
    """A directed edge still connects its endpoints for MST purposes."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=1.0, directed=True))

    algorithm = KruskalMST(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.total_weight == 1.0


def test_parallel_edges_are_both_considered() -> None:
    """Parallel edges are separate candidates; only the cheaper is used."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0))
    graph.add_edge(Edge(source=1, target=2, weight=2.0))

    algorithm = KruskalMST(graph, start_node_id=1)
    steps = run_to_completion(algorithm)

    assert algorithm.total_weight == 2.0
    assert len(steps) == 2
    assert "Rejected" in steps[-1].info


def test_current_edge_is_reported() -> None:
    """Every step reports the edge being considered."""
    algorithm = KruskalMST(build_chain(), start_node_id=1)
    first = algorithm.step()

    assert first.current_edge is not None
    assert first.current_edge in {(1, 2), (2, 3)}


def test_info_reports_running_total() -> None:
    """Accepted steps include the running total weight."""
    algorithm = KruskalMST(build_chain(), start_node_id=1)
    first = algorithm.step()

    assert "total" in first.info


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = KruskalMST(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
