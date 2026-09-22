"""Tests for the iterative breadth-first search."""

import pytest

from application.algorithms.breadth_first_search import BreadthFirstSearch
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return a graph 1-2-3 in a straight line."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    return graph


def build_star() -> Graph:
    """Return a graph where node 1 connects to nodes 2 and 3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))
    return graph


def build_diamond() -> Graph:
    """Return a diamond: 1-2, 1-3, 2-4, 3-4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=3))
    graph.add_edge(Edge(source=2, target=4))
    graph.add_edge(Edge(source=3, target=4))
    return graph


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Start node 42"):
        BreadthFirstSearch(graph, start_node_id=42)


def test_single_node_graph_finishes_in_one_step() -> None:
    """A graph with one node produces a single step."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = BreadthFirstSearch(graph, start_node_id=1)
    result = algorithm.step()

    assert result.current == 1
    assert result.visited == frozenset({1})
    assert result.frontier == ()
    assert algorithm.is_finished is True


def test_chain_visits_nodes_in_order() -> None:
    """A straight chain is traversed from start to end."""
    algorithm = BreadthFirstSearch(build_chain(), start_node_id=1)

    first = algorithm.step()
    assert first.current == 1
    assert first.visited == frozenset({1})
    assert first.frontier == (2,)

    second = algorithm.step()
    assert second.current == 2
    assert second.visited == frozenset({1, 2})
    assert second.frontier == (3,)

    third = algorithm.step()
    assert third.current == 3
    assert third.visited == frozenset({1, 2, 3})
    assert third.frontier == ()
    assert algorithm.is_finished is True


def test_star_visits_leaves_in_order() -> None:
    """A star is traversed level by level: center, then leaves."""
    algorithm = BreadthFirstSearch(build_star(), start_node_id=1)

    first = algorithm.step()
    assert first.current == 1
    assert first.frontier == (2, 3)

    second = algorithm.step()
    assert second.current == 2
    assert second.frontier == (3,)

    third = algorithm.step()
    assert third.current == 3
    assert third.frontier == ()
    assert algorithm.is_finished is True


def test_diamond_visits_nodes_level_by_level() -> None:
    """A diamond is traversed in BFS order: 1, then 2 and 3, then 4."""
    algorithm = BreadthFirstSearch(build_diamond(), start_node_id=1)

    visited_sequence: list[int] = []
    while not algorithm.is_finished:
        result = algorithm.step()
        assert result.current is not None
        visited_sequence.append(result.current)

    assert visited_sequence == [1, 2, 3, 4]
    assert algorithm.is_finished is True


def test_step_after_finish_raises() -> None:
    """Calling step after the traversal finished raises RuntimeError."""
    algorithm = BreadthFirstSearch(build_chain(), start_node_id=1)
    while not algorithm.is_finished:
        algorithm.step()

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_unreachable_nodes_are_not_visited() -> None:
    """Nodes in a separate component are not reached from the start."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    algorithm = BreadthFirstSearch(graph, start_node_id=1)
    result = algorithm.step()

    assert result.visited == frozenset({1})
    assert algorithm.is_finished is True


def test_tree_edges_form_the_traversal_tree() -> None:
    """Tree edges contain exactly the edges used during traversal."""
    algorithm = BreadthFirstSearch(build_chain(), start_node_id=1)

    last_result = algorithm.step()
    while not algorithm.is_finished:
        last_result = algorithm.step()

    assert last_result.tree_edges == frozenset({(1, 2), (2, 3)})


def test_diamond_does_not_revisit_shared_node() -> None:
    """Node 4 is discovered once, from node 2, not from node 3."""
    algorithm = BreadthFirstSearch(build_diamond(), start_node_id=1)

    algorithm.step()
    algorithm.step()
    third = algorithm.step()

    assert (3, 4) not in third.tree_edges
    assert (2, 4) in third.tree_edges


def test_info_is_human_readable() -> None:
    """Each step carries a description mentioning the current node."""
    algorithm = BreadthFirstSearch(build_chain(), start_node_id=1)
    result = algorithm.step()

    assert result.info == "Visited node 1"
