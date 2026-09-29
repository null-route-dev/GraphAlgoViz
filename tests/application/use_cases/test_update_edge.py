"""Tests for the UpdateEdgeUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.update_edge import UpdateEdgeUseCase
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


def test_update_edge_changes_weight(
    repository: GraphRepository,
) -> None:
    """The edge's weight is replaced with the new value."""
    UpdateEdgeUseCase(repository).execute(
        source=1, target=2, weight=7.5, directed=False
    )

    edge = repository.get().edges()[0]
    assert edge.weight == 7.5


def test_update_edge_returns_new_edge(
    repository: GraphRepository,
) -> None:
    """execute returns the new edge with the updated attributes."""
    edge = UpdateEdgeUseCase(repository).execute(
        source=1, target=2, weight=3.0, directed=False
    )

    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 3.0
    assert edge.directed is False


def test_update_edge_works_in_reverse_order(
    repository: GraphRepository,
) -> None:
    """For an undirected edge, reversed arguments still work."""
    UpdateEdgeUseCase(repository).execute(
        source=2, target=1, weight=4.0, directed=False
    )

    edge = repository.get().edges()[0]
    assert edge.weight == 4.0


def test_update_edge_sets_directed_flag(
    repository: GraphRepository,
) -> None:
    """The directed flag is set to the value passed in."""
    UpdateEdgeUseCase(repository).execute(source=1, target=2, weight=1.0, directed=True)

    edge = repository.get().edges()[0]
    assert edge.directed is True


def test_update_edge_can_make_directed_edge_undirected(
    repository: GraphRepository,
) -> None:
    """A directed edge can become undirected."""
    graph = repository.get()
    graph.remove_edge(1, 2)
    AddEdgeUseCase(repository).execute(source=1, target=2, weight=1.0, directed=True)

    UpdateEdgeUseCase(repository).execute(
        source=1, target=2, weight=1.0, directed=False
    )

    edge = repository.get().edges()[0]
    assert edge.directed is False


def test_update_edge_raises_for_missing_edge(
    repository: GraphRepository,
) -> None:
    """Updating a missing edge raises KeyError."""
    repository.get().remove_edge(1, 2)

    with pytest.raises(KeyError):
        UpdateEdgeUseCase(repository).execute(
            source=1, target=2, weight=5.0, directed=False
        )


def test_update_edge_keeps_edge_count(
    repository: GraphRepository,
) -> None:
    """The number of edges is unchanged after updating."""
    UpdateEdgeUseCase(repository).execute(
        source=1, target=2, weight=2.0, directed=False
    )

    assert repository.get().edge_count == 1


def test_update_directed_edge_requires_correct_order(
    repository: GraphRepository,
) -> None:
    """A directed edge is not found when arguments are reversed."""
    graph = repository.get()
    graph.remove_edge(1, 2)
    AddEdgeUseCase(repository).execute(source=1, target=2, weight=1.0, directed=True)

    with pytest.raises(KeyError):
        UpdateEdgeUseCase(repository).execute(
            source=2, target=1, weight=5.0, directed=True
        )
