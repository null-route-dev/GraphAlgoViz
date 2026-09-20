"""Tests for the RemoveEdgeUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
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
    AddEdgeUseCase(repo).execute(source=1, target=2)
    return repo


def test_remove_edge_removes_it_from_repository(
    repository: GraphRepository,
) -> None:
    """The edge is gone after execute."""
    RemoveEdgeUseCase(repository).execute(source=1, target=2)
    assert repository.get().edge_count == 0


def test_remove_edge_undirected_reverse_order(
    repository: GraphRepository,
) -> None:
    """Removing an undirected edge works in reverse order too."""
    RemoveEdgeUseCase(repository).execute(source=2, target=1)
    assert repository.get().edge_count == 0


def test_remove_edge_keeps_nodes(
    repository: GraphRepository,
) -> None:
    """Removing an edge does not affect the nodes."""
    RemoveEdgeUseCase(repository).execute(source=1, target=2)
    assert repository.get().node_count == 2


def test_remove_edge_raises_for_missing_edge(
    repository: GraphRepository,
) -> None:
    """Removing an edge that does not exist raises KeyError."""
    RemoveEdgeUseCase(repository).execute(source=1, target=2)
    with pytest.raises(KeyError):
        RemoveEdgeUseCase(repository).execute(source=1, target=2)
