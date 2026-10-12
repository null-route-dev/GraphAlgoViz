"""Tests for the UpdateNodeUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.update_node import UpdateNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a repository with two nodes and one edge."""
    repo = InMemoryGraphRepository()
    add_node = AddNodeUseCase(repo)
    add_node.execute(node_id=1, label="A")
    add_node.execute(node_id=2, label="B")
    AddEdgeUseCase(repo).execute(source=1, target=2)
    return repo


def test_update_node_changes_label(repository: GraphRepository) -> None:
    """The node's label is replaced with the new value."""
    UpdateNodeUseCase(repository).execute(node_id=1, label="Z")

    assert repository.get().node(1).label == "Z"


def test_update_node_returns_new_node(repository: GraphRepository) -> None:
    """execute returns the new node."""
    node = UpdateNodeUseCase(repository).execute(node_id=1, label="Z")

    assert node.id == 1
    assert node.label == "Z"


def test_update_node_keeps_edges(repository: GraphRepository) -> None:
    """Edges incident to the node are not affected."""
    UpdateNodeUseCase(repository).execute(node_id=1, label="Z")

    assert repository.get().edge_count == 1


def test_update_node_raises_for_missing_node(
    repository: GraphRepository,
) -> None:
    """Updating a missing node raises KeyError."""
    with pytest.raises(KeyError):
        UpdateNodeUseCase(repository).execute(node_id=42, label="Z")


def test_update_node_keeps_node_count(repository: GraphRepository) -> None:
    """The number of nodes is unchanged after updating."""
    UpdateNodeUseCase(repository).execute(node_id=1, label="Z")

    assert repository.get().node_count == 2
