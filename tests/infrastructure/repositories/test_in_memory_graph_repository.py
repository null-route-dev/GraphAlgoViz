"""Tests for the in-memory graph repository."""

import pytest

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> InMemoryGraphRepository:
    """Return a fresh in-memory repository."""
    return InMemoryGraphRepository()


def test_new_repository_returns_empty_graph(
    repository: InMemoryGraphRepository,
) -> None:
    """A fresh repository returns an empty graph."""
    graph = repository.get()
    assert graph.node_count == 0
    assert graph.edge_count == 0


def test_save_then_get_returns_same_graph(
    repository: InMemoryGraphRepository,
) -> None:
    """After save, get returns the stored graph."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A"))
    repository.save(graph)

    assert repository.get() is graph


def test_save_replaces_previous_graph(
    repository: InMemoryGraphRepository,
) -> None:
    """Saving a second graph replaces the first one."""
    first = Graph()
    first.add_node(Node(id=1))
    repository.save(first)

    second = Graph()
    second.add_node(Node(id=2))
    repository.save(second)

    stored = repository.get()
    assert stored is second
    assert stored.has_node(1) is False
    assert stored.has_node(2) is True


def test_get_returns_same_instance_across_calls(
    repository: InMemoryGraphRepository,
) -> None:
    """Repeated calls to get return the same instance."""
    assert repository.get() is repository.get()


def test_mutations_are_visible_through_repository(
    repository: InMemoryGraphRepository,
) -> None:
    """Mutating the returned graph affects subsequent reads."""
    graph = repository.get()
    graph.add_node(Node(id=1, label="A"))

    assert repository.get().has_node(1) is True


def test_clear_resets_to_empty_graph(
    repository: InMemoryGraphRepository,
) -> None:
    """After clear, the repository returns an empty graph."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_edge(Edge(source=1, target=1))
    repository.save(graph)

    repository.clear()

    stored = repository.get()
    assert stored.node_count == 0
    assert stored.edge_count == 0


def test_clear_returns_new_instance(
    repository: InMemoryGraphRepository,
) -> None:
    """After clear, the repository returns a different graph instance."""
    original = repository.get()
    repository.clear()

    assert repository.get() is not original
