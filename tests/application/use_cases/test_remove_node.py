"""Tests for the RemoveNodeUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a fresh in-memory repository."""
    return InMemoryGraphRepository()


def test_remove_node_removes_it_from_repository(
    repository: GraphRepository,
) -> None:
    """The node is gone after execute."""
    AddNodeUseCase(repository).execute(node_id=1)
    RemoveNodeUseCase(repository).execute(node_id=1)
    assert repository.get().has_node(1) is False


def test_remove_node_removes_incident_edges(
    repository: GraphRepository,
) -> None:
    """Edges incident to the removed node are removed as well."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    AddEdgeUseCase(repository).execute(source=1, target=2)

    RemoveNodeUseCase(repository).execute(node_id=1)

    assert repository.get().edge_count == 0


def test_remove_node_raises_for_missing_node(
    repository: GraphRepository,
) -> None:
    """Removing a node that does not exist raises KeyError."""
    with pytest.raises(KeyError):
        RemoveNodeUseCase(repository).execute(node_id=42)
