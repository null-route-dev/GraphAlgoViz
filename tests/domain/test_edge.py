"""Tests for the Edge entity."""

import pytest

from domain.entities.edge import Edge


def test_create_edge_with_defaults() -> None:
    """Edge has weight 1.0 and is undirected by default."""
    edge = Edge(source=1, target=2)
    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 1.0
    assert edge.directed is False


def test_create_edge_with_all_parameters() -> None:
    """Edge stores all provided parameters."""
    edge = Edge(source=1, target=2, weight=3.5, directed=True)
    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 3.5
    assert edge.directed is True


def test_connects_returns_true_for_source() -> None:
    """connects returns True when the given node is the source."""
    edge = Edge(source=1, target=2)
    assert edge.connects(1) is True


def test_connects_returns_true_for_target() -> None:
    """connects returns True when the given node is the target."""
    edge = Edge(source=1, target=2)
    assert edge.connects(2) is True


def test_connects_returns_false_for_unrelated_node() -> None:
    """connects returns False for a node not incident to the edge."""
    edge = Edge(source=1, target=2)
    assert edge.connects(3) is False


def test_other_end_returns_target_when_given_source() -> None:
    """other_end returns the target when the source is provided."""
    edge = Edge(source=1, target=2)
    assert edge.other_end(1) == 2


def test_other_end_returns_source_when_given_target() -> None:
    """other_end returns the source when the target is provided."""
    edge = Edge(source=1, target=2)
    assert edge.other_end(2) == 1


def test_other_end_raises_for_unrelated_node() -> None:
    """other_end raises ValueError for a node not incident to the edge."""
    edge = Edge(source=1, target=2)
    with pytest.raises(ValueError, match="not incident"):
        edge.other_end(3)
