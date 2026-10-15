"""Tests for Kuhn's maximum bipartite matching algorithm."""

import pytest

from application.algorithms.bipartite_matching import (
    MATCHED_COLOR,
    ON_PATH_COLOR,
    BipartiteMatching,
)
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_path() -> Graph:
    """Return an undirected path 1-2-3-4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=4))
    return graph


def build_k22() -> Graph:
    """Return the complete bipartite graph K2,2."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=3))
    graph.add_edge(Edge(source=1, target=4))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=2, target=4))
    return graph


def build_k33() -> Graph:
    """Return the complete bipartite graph K3,3."""
    graph = Graph()
    for node_id in range(1, 7):
        graph.add_node(Node(id=node_id))
    for left in (1, 2, 3):
        for right in (4, 5, 6):
            graph.add_edge(Edge(source=left, target=right))
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
    """Return two disconnected edges 1-2 and 3-4."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=3, target=4))
    return graph


def build_odd_cycle() -> Graph:
    """Return an undirected triangle."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=3, target=1))
    return graph


def run_to_completion(algorithm: BipartiteMatching) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_path()
    with pytest.raises(ValueError, match="Start node 42"):
        BipartiteMatching(graph, start_node_id=42)


def test_non_bipartite_graph_raises() -> None:
    """A non-bipartite graph raises ValueError at construction."""
    with pytest.raises(ValueError, match="not bipartite"):
        BipartiteMatching(build_odd_cycle(), start_node_id=1)


def test_single_node_has_empty_matching() -> None:
    """A single-node graph has a matching of size zero."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = BipartiteMatching(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 0


def test_single_edge_matches() -> None:
    """Two nodes connected by an edge give a matching of size one."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BipartiteMatching(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 1


def test_path_matching_size() -> None:
    """A four-node path yields a matching of size two."""
    algorithm = BipartiteMatching(build_path(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 2


def test_k22_matching_size() -> None:
    """K2,2 yields a matching of size two."""
    algorithm = BipartiteMatching(build_k22(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 2


def test_k33_matching_size() -> None:
    """K3,3 yields a matching of size three."""
    algorithm = BipartiteMatching(build_k33(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 3


def test_star_matching_size() -> None:
    """A star yields a matching of size one."""
    algorithm = BipartiteMatching(build_star(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 1


def test_two_components_matching_size() -> None:
    """Two disconnected edges yield a matching of size two."""
    algorithm = BipartiteMatching(build_two_components(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 2


def test_matched_pairs_are_disjoint() -> None:
    """No node appears in more than one matched pair."""
    algorithm = BipartiteMatching(build_k33(), start_node_id=1)
    run_to_completion(algorithm)

    pairs = algorithm.matched_pairs()
    lefts = [pair[0] for pair in pairs]
    rights = [pair[1] for pair in pairs]

    assert len(lefts) == len(set(lefts))
    assert len(rights) == len(set(rights))


def test_matched_pairs_are_sorted() -> None:
    """Matched pairs are returned sorted by left node id."""
    algorithm = BipartiteMatching(build_k33(), start_node_id=1)
    run_to_completion(algorithm)

    pairs = algorithm.matched_pairs()
    assert pairs == sorted(pairs)


def test_matched_nodes_are_colored() -> None:
    """Matched nodes receive the matched color in the final snapshot."""
    algorithm = BipartiteMatching(build_k33(), start_node_id=1)
    steps = run_to_completion(algorithm)
    colors = steps[-1].node_colors

    for left_node, right_node in algorithm.matched_pairs():
        assert colors[left_node] == MATCHED_COLOR
        assert colors[right_node] == MATCHED_COLOR


def test_dfs_stack_nodes_use_on_path_color() -> None:
    """Left nodes on the active DFS path receive the on-path color."""
    algorithm = BipartiteMatching(build_k33(), start_node_id=1)
    first = algorithm.step()

    assert first.node_colors.get(1) == ON_PATH_COLOR


def test_info_reports_matching_size_at_end() -> None:
    """The final step reports the matching size."""
    algorithm = BipartiteMatching(build_k22(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "Maximum matching size = 2" in steps[-1].info


def test_parallel_edges_collapse() -> None:
    """Parallel edges between the same left and right node count once."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=1, target=2))

    algorithm = BipartiteMatching(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.matching_size() == 1


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = BipartiteMatching(build_k22(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
