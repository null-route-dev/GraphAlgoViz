"""Tests for the AddNodeUseCase."""

import pytest

from application.use_cases.add_node import AddNodeUseCase
from domain.interfaces.graph_repository import GraphRepository
from infrastructure.repositories.in_memory_graph_repository import (
    InMemoryGraphRepository,
)


@pytest.fixture
def repository() -> GraphRepository:
    """Return a fresh in-memory repository."""
    return InMemoryGraphRepository()


@pytest.fixture
def use_case(repository: GraphRepository) -> AddNodeUseCase:
    """Return an AddNodeUseCase wired to the in-memory repository."""
    return AddNodeUseCase(repository)


def test_add_node_stores_it_in_repository(
    repository: GraphRepository,
    use_case: AddNodeUseCase,
) -> None:
    """The node appears in the repository after execute."""
    use_case.execute(node_id=1, label="A")
    assert repository.get().has_node(1) is True


def test_add_node_returns_the_created_node(
    use_case: AddNodeUseCase,
) -> None:
    """execute returns the created node."""
    node = use_case.execute(node_id=1, label="A")
    assert node.id == 1
    assert node.label == "A"


def test_add_node_with_default_label(
    repository: GraphRepository,
    use_case: AddNodeUseCase,
) -> None:
    """Label defaults to an empty string."""
    use_case.execute(node_id=1)
    assert repository.get().node(1).label == ""


def test_add_node_raises_for_duplicate_id(
    use_case: AddNodeUseCase,
) -> None:
    """Adding a node with an existing id raises ValueError."""
    use_case.execute(node_id=1)
    with pytest.raises(ValueError, match="already exists"):
        use_case.execute(node_id=1)


def test_add_node_does_not_modify_existing_node(
    repository: GraphRepository,
    use_case: AddNodeUseCase,
) -> None:
    """A failed duplicate add leaves the original node intact."""
    use_case.execute(node_id=1, label="Original")
    with pytest.raises(ValueError):
        use_case.execute(node_id=1, label="Replacement")
    assert repository.get().node(1).label == "Original"
