"""Tests for the RemoveIsolatedNodesUseCase."""

import pytest

from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_isolated_nodes import (
    RemoveIsolatedNodesUseCase,
)
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a fresh in-memory repository."""
    return InMemoryGraphRepository()


def test_empty_graph_returns_empty_list(
    repository: GraphRepository,
) -> None:
    """An empty graph has no nodes to remove."""
    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == []


def test_fully_connected_graph_returns_empty_list(
    repository: GraphRepository,
) -> None:
    """A connected graph has no isolated nodes."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    AddEdgeUseCase(repository).execute(source=1, target=2)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == []
    assert repository.get().node_count == 2


def test_all_nodes_isolated_removes_everything(
    repository: GraphRepository,
) -> None:
    """A graph with no edges loses all its nodes."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    add_node.execute(node_id=3)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == [1, 2, 3]
    assert repository.get().node_count == 0


def test_mixed_graph_removes_only_isolated(
    repository: GraphRepository,
) -> None:
    """Only isolated nodes are removed; connected ones stay."""
    add_node = AddNodeUseCase(repository)
    for node_id in (1, 2, 3, 4, 5):
        add_node.execute(node_id=node_id)
    AddEdgeUseCase(repository).execute(source=2, target=3)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == [1, 4, 5]
    assert repository.get().node_count == 2
    assert repository.get().has_node(2) is True
    assert repository.get().has_node(3) is True


def test_self_loop_keeps_node(
    repository: GraphRepository,
) -> None:
    """A node with only a self-loop is not isolated."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    AddEdgeUseCase(repository).execute(source=1, target=1)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == []
    assert repository.get().node_count == 1


def test_incoming_directed_edge_keeps_node(
    repository: GraphRepository,
) -> None:
    """A node with only incoming directed edges is not isolated."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    AddEdgeUseCase(repository).execute(source=1, target=2, directed=True)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == []
    assert repository.get().node_count == 2


def test_outgoing_directed_edge_keeps_node(
    repository: GraphRepository,
) -> None:
    """A node with only outgoing directed edges is not isolated."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    AddEdgeUseCase(repository).execute(source=1, target=2, directed=True)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == []
    assert repository.get().node_count == 2


def test_removed_ids_are_sorted(
    repository: GraphRepository,
) -> None:
    """The returned ids are in ascending order."""
    add_node = AddNodeUseCase(repository)
    for node_id in (5, 2, 9, 1):
        add_node.execute(node_id=node_id)

    removed = RemoveIsolatedNodesUseCase(repository).execute()

    assert removed == [1, 2, 5, 9]


def test_edges_are_not_touched(
    repository: GraphRepository,
) -> None:
    """Removing isolated nodes does not affect existing edges."""
    add_node = AddNodeUseCase(repository)
    add_node.execute(node_id=1)
    add_node.execute(node_id=2)
    add_node.execute(node_id=3)
    AddEdgeUseCase(repository).execute(source=1, target=2)

    RemoveIsolatedNodesUseCase(repository).execute()

    assert repository.get().edge_count == 1
