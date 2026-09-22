"""Tests for the algorithm registry."""

import pytest

from application.algorithms.breadth_first_search import BreadthFirstSearch
from application.algorithms.depth_first_search import DepthFirstSearch
from application.algorithms.dijkstra import Dijkstra
from application.algorithms.registry import (
    AlgorithmInfo,
    AlgorithmRegistry,
    build_default_registry,
)
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_chain() -> Graph:
    """Return a graph 1-2-3 in a straight line."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    return graph


def make_info(algorithm_id: str) -> AlgorithmInfo:
    """Return AlgorithmInfo with the given id and a DFS factory."""
    return AlgorithmInfo(
        id=algorithm_id,
        display_name=algorithm_id.upper(),
        description=f"Description of {algorithm_id}",
        factory=DepthFirstSearch,
    )


def test_register_and_get() -> None:
    """A registered algorithm can be retrieved by id."""
    registry = AlgorithmRegistry()
    info = make_info("dfs")
    registry.register(info)

    assert registry.get("dfs") is info


def test_register_rejects_duplicate_id() -> None:
    """Registering two algorithms with the same id raises ValueError."""
    registry = AlgorithmRegistry()
    registry.register(make_info("dfs"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(make_info("dfs"))


def test_get_raises_for_unknown_id() -> None:
    """Requesting an unregistered id raises KeyError."""
    registry = AlgorithmRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.get("unknown")


def test_create_returns_algorithm_instance() -> None:
    """create builds an algorithm from the registered factory."""
    registry = AlgorithmRegistry()
    registry.register(make_info("dfs"))

    algorithm = registry.create("dfs", build_chain(), start_node_id=1)

    assert isinstance(algorithm, DepthFirstSearch)


def test_create_raises_for_unknown_id() -> None:
    """create with an unregistered id raises KeyError."""
    registry = AlgorithmRegistry()

    with pytest.raises(KeyError):
        registry.create("unknown", build_chain(), start_node_id=1)


def test_all_returns_algorithms_in_registration_order() -> None:
    """all preserves the order in which algorithms were registered."""
    registry = AlgorithmRegistry()
    registry.register(make_info("alpha"))
    registry.register(make_info("beta"))
    registry.register(make_info("gamma"))

    assert [info.id for info in registry.all()] == ["alpha", "beta", "gamma"]


def test_all_returns_empty_list_for_new_registry() -> None:
    """A fresh registry reports no algorithms."""
    registry = AlgorithmRegistry()

    assert registry.all() == []


def test_count_reflects_registered_algorithms() -> None:
    """count matches the number of registered algorithms."""
    registry = AlgorithmRegistry()
    assert registry.count == 0

    registry.register(make_info("alpha"))
    registry.register(make_info("beta"))

    assert registry.count == 2


def test_default_registry_contains_builtin_algorithms() -> None:
    """The default registry exposes dfs, bfs, and dijkstra in order."""
    registry = build_default_registry()

    assert [info.id for info in registry.all()] == ["dfs", "bfs", "dijkstra"]


def test_default_registry_describes_each_algorithm() -> None:
    """Every built-in algorithm has a non-empty display name and description."""
    registry = build_default_registry()

    for info in registry.all():
        assert info.display_name
        assert info.description


def test_default_registry_creates_each_algorithm() -> None:
    """The default registry can instantiate every built-in algorithm."""
    registry = build_default_registry()
    graph = build_chain()

    assert isinstance(registry.create("dfs", graph, 1), DepthFirstSearch)
    assert isinstance(registry.create("bfs", graph, 1), BreadthFirstSearch)
    assert isinstance(registry.create("dijkstra", graph, 1), Dijkstra)
