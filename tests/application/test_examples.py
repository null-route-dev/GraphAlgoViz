"""Tests for the example graph factories."""

from typing import Any

import pytest

from application.examples import (
    all_examples,
    build_binary_tree,
    build_cycle,
    build_dodecahedron,
    build_k5,
    build_k33,
    build_petersen,
    find_example,
)


def _all_in_unit_square(positions: dict[int, Any]) -> bool:
    return all(
        0.0 <= pos.x <= 1.0 and 0.0 <= pos.y <= 1.0 for pos in positions.values()
    )


def test_k5_counts() -> None:
    """K5 has five nodes and ten edges."""
    graph, _ = build_k5()
    assert graph.node_count == 5
    assert graph.edge_count == 10


def test_k5_positions_inside_unit_square() -> None:
    """Every K5 position lies in the unit square."""
    _, positions = build_k5()
    assert len(positions) == 5
    assert _all_in_unit_square(positions)


def test_k33_counts() -> None:
    """K3,3 has six nodes and nine edges."""
    graph, _ = build_k33()
    assert graph.node_count == 6
    assert graph.edge_count == 9


def test_k33_is_bipartite() -> None:
    """Every K3,3 edge joins a left node to a right node."""
    graph, _ = build_k33()
    left = {1, 2, 3}
    right = {4, 5, 6}
    for edge in graph.edges():
        assert (edge.source in left and edge.target in right) or (
            edge.source in right and edge.target in left
        )


def test_binary_tree_counts() -> None:
    """The depth-2 binary tree has seven nodes and six edges."""
    graph, _ = build_binary_tree()
    assert graph.node_count == 7
    assert graph.edge_count == 6


def test_binary_tree_is_tree() -> None:
    """A tree has one more node than edge."""
    graph, _ = build_binary_tree()
    assert graph.node_count == graph.edge_count + 1


def test_cycle_counts() -> None:
    """C6 has six nodes and six edges."""
    graph, _ = build_cycle()
    assert graph.node_count == 6
    assert graph.edge_count == 6


def test_cycle_all_degree_two() -> None:
    """Every node in a cycle has exactly two neighbors."""
    graph, _ = build_cycle()
    for node_id in range(1, 7):
        assert len(graph.neighbors(node_id)) == 2


def test_petersen_counts() -> None:
    """The Petersen graph has ten nodes and fifteen edges."""
    graph, _ = build_petersen()
    assert graph.node_count == 10
    assert graph.edge_count == 15


def test_petersen_all_degree_three() -> None:
    """Every node in the Petersen graph has degree three."""
    graph, _ = build_petersen()
    for node_id in range(1, 11):
        assert len(graph.neighbors(node_id)) == 3


def test_petersen_positions_inside_unit_square() -> None:
    """Every Petersen position lies in the unit square."""
    _, positions = build_petersen()
    assert len(positions) == 10
    assert _all_in_unit_square(positions)


def test_dodecahedron_counts() -> None:
    """The dodecahedral graph has twenty nodes and thirty edges."""
    graph, _ = build_dodecahedron()
    assert graph.node_count == 20
    assert graph.edge_count == 30


def test_dodecahedron_all_degree_three() -> None:
    """Every node in the dodecahedral graph has degree three."""
    graph, _ = build_dodecahedron()
    for node_id in range(1, 21):
        assert len(graph.neighbors(node_id)) == 3


def test_all_examples_has_six_entries() -> None:
    """The example catalogue exposes six graphs."""
    assert len(all_examples()) == 6


def test_all_examples_have_unique_ids() -> None:
    """Every example uses a distinct id."""
    ids = [example.id for example in all_examples()]
    assert len(ids) == len(set(ids))


def test_every_example_builds() -> None:
    """Every example builds without error and covers all nodes."""
    for example in all_examples():
        graph, positions = example.build()
        assert graph.node_count > 0
        assert len(positions) == graph.node_count


def test_find_example_returns_match() -> None:
    """find_example returns the matching example."""
    example = find_example("k5")
    assert example.id == "k5"
    assert "K5" in example.display_name


def test_find_example_raises_for_unknown() -> None:
    """find_example raises KeyError for an unknown id."""
    with pytest.raises(KeyError):
        find_example("no-such-example")
