"""Tests for the SetEdgeWeightUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.set_edge_weight import SetEdgeWeightUseCase
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a fresh in-memory repository with two nodes and one edge."""
    repo = InMemoryGraphRepository()
    add_node = AddNodeUseCase(repo)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    AddEdgeUseCase(repo).execute(source=1, target=2, weight=1.0)
    return repo


def test_set_edge_weight_updates_value(
    repository: GraphRepository,
) -> None:
    """The edge's weight is replaced with the new value."""
    SetEdgeWeightUseCase(repository).execute(source=1, target=2, weight=7.5)

    edge = repository.get().edges()[0]
    assert edge.weight == 7.5


def test_set_edge_weight_returns_new_edge(
    repository: GraphRepository,
) -> None:
    """execute returns the new edge with the updated weight."""
    edge = SetEdgeWeightUseCase(repository).execute(source=1, target=2, weight=3.0)

    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 3.0


def test_set_edge_weight_works_in_reverse_order(
    repository: GraphRepository,
) -> None:
    """For an undirected edge, reversed arguments still work."""
    SetEdgeWeightUseCase(repository).execute(source=2, target=1, weight=4.0)

    edge = repository.get().edges()[0]
    assert edge.weight == 4.0


def test_set_edge_weight_preserves_directed_flag(
    repository: GraphRepository,
) -> None:
    """The directed flag of the original edge is kept."""
    graph = repository.get()
    graph.remove_edge(1, 2)
    AddEdgeUseCase(repository).execute(source=1, target=2, weight=1.0, directed=True)

    SetEdgeWeightUseCase(repository).execute(source=1, target=2, weight=9.0)

    edge = repository.get().edges()[0]
    assert edge.directed is True


def test_set_edge_weight_raises_for_missing_edge(
    repository: GraphRepository,
) -> None:
    """Setting the weight of a missing edge raises KeyError."""
    repository.get().remove_edge(1, 2)

    with pytest.raises(KeyError):
        SetEdgeWeightUseCase(repository).execute(source=1, target=2, weight=5.0)


def test_set_edge_weight_keeps_edge_count(
    repository: GraphRepository,
) -> None:
    """The number of edges is unchanged after setting the weight."""
    SetEdgeWeightUseCase(repository).execute(source=1, target=2, weight=2.0)

    assert repository.get().edge_count == 1
