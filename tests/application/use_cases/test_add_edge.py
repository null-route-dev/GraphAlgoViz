"""Tests for the AddEdgeUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a fresh in-memory repository with two nodes."""
    repo = InMemoryGraphRepository()
    add_node = AddNodeUseCase(repo)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    return repo


def test_add_edge_stores_it_in_repository(
    repository: GraphRepository,
) -> None:
    """The edge appears in the repository after execute."""
    AddEdgeUseCase(repository).execute(source=1, target=2)
    assert repository.get().edge_count == 1


def test_add_edge_returns_the_created_edge(
    repository: GraphRepository,
) -> None:
    """execute returns the created edge."""
    edge = AddEdgeUseCase(repository).execute(
        source=1, target=2, weight=3.5, directed=True
    )
    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 3.5
    assert edge.directed is True


def test_add_edge_default_weight_and_direction(
    repository: GraphRepository,
) -> None:
    """Weight defaults to 1.0 and direction to False."""
    edge = AddEdgeUseCase(repository).execute(source=1, target=2)
    assert edge.weight == 1.0
    assert edge.directed is False


def test_add_edge_raises_for_missing_source(
    repository: GraphRepository,
) -> None:
    """Adding an edge with a missing source raises ValueError."""
    with pytest.raises(ValueError, match="Source node 42"):
        AddEdgeUseCase(repository).execute(source=42, target=2)


def test_add_edge_raises_for_missing_target(
    repository: GraphRepository,
) -> None:
    """Adding an edge with a missing target raises ValueError."""
    with pytest.raises(ValueError, match="Target node 42"):
        AddEdgeUseCase(repository).execute(source=1, target=42)
