"""Tests for the random graph generators."""

import pytest

from application.generators import (
    GeneratorKind,
    GeneratorRequest,
    generate,
    generate_barabasi_albert,
    generate_erdos_renyi,
    generate_watts_strogatz,
)


def test_erdos_renyi_node_count() -> None:
    """Every node id is present in the generated graph."""
    graph = generate_erdos_renyi(10, 0.5, seed=42)
    assert graph.node_count == 10


def test_erdos_renyi_zero_probability_has_no_edges() -> None:
    """Probability 0 produces no edges."""
    graph = generate_erdos_renyi(10, 0.0, seed=1)
    assert graph.edge_count == 0


def test_erdos_renyi_unit_probability_is_complete() -> None:
    """Probability 1 produces a complete graph."""
    graph = generate_erdos_renyi(6, 1.0, seed=1)
    assert graph.edge_count == 15


def test_erdos_renyi_is_deterministic_with_seed() -> None:
    """The same seed produces the same edges."""
    first = generate_erdos_renyi(15, 0.3, seed=7)
    second = generate_erdos_renyi(15, 0.3, seed=7)
    assert first.edges() == second.edges()


def test_erdos_renyi_rejects_small_node_count() -> None:
    """Fewer than two nodes is rejected."""
    with pytest.raises(ValueError):
        generate_erdos_renyi(1, 0.5)


def test_erdos_renyi_rejects_invalid_probability() -> None:
    """Probabilities outside [0, 1] are rejected."""
    with pytest.raises(ValueError):
        generate_erdos_renyi(5, -0.1)
    with pytest.raises(ValueError):
        generate_erdos_renyi(5, 1.1)


def test_barabasi_albert_edge_count() -> None:
    """Edge count follows the standard formula for preferential attachment."""
    graph = generate_barabasi_albert(10, 2, seed=42)
    assert graph.node_count == 10
    assert graph.edge_count == 17


def test_barabasi_albert_is_deterministic_with_seed() -> None:
    """The same seed produces the same edges."""
    first = generate_barabasi_albert(15, 2, seed=13)
    second = generate_barabasi_albert(15, 2, seed=13)
    assert first.edges() == second.edges()


def test_barabasi_albert_rejects_small_node_count() -> None:
    """Fewer than two nodes is rejected."""
    with pytest.raises(ValueError):
        generate_barabasi_albert(1, 1)


def test_barabasi_albert_rejects_invalid_attachment() -> None:
    """Attachment counts outside [1, node_count - 1] are rejected."""
    with pytest.raises(ValueError):
        generate_barabasi_albert(5, 0)
    with pytest.raises(ValueError):
        generate_barabasi_albert(5, 5)


def test_watts_strogatz_no_rewiring_has_ring_edges() -> None:
    """Zero rewiring leaves the original ring with n*k/2 edges."""
    graph = generate_watts_strogatz(10, 4, 0.0, seed=1)
    assert graph.edge_count == 20


def test_watts_strogatz_full_rewiring_keeps_edge_count() -> None:
    """Rewiring preserves the total number of edges."""
    graph = generate_watts_strogatz(12, 4, 1.0, seed=1)
    assert graph.edge_count == 24


def test_watts_strogatz_is_deterministic_with_seed() -> None:
    """The same seed produces the same edges."""
    first = generate_watts_strogatz(12, 4, 0.3, seed=5)
    second = generate_watts_strogatz(12, 4, 0.3, seed=5)
    assert first.edges() == second.edges()


def test_watts_strogatz_rejects_small_node_count() -> None:
    """Fewer than four nodes is rejected."""
    with pytest.raises(ValueError):
        generate_watts_strogatz(3, 2, 0.1)


def test_watts_strogatz_rejects_odd_neighbors() -> None:
    """Odd neighbor counts are rejected."""
    with pytest.raises(ValueError):
        generate_watts_strogatz(10, 3, 0.1)


def test_watts_strogatz_rejects_neighbors_at_least_n() -> None:
    """Neighbor counts not smaller than node_count are rejected."""
    with pytest.raises(ValueError):
        generate_watts_strogatz(10, 10, 0.1)


def test_watts_strogatz_rejects_invalid_rewiring() -> None:
    """Rewiring probabilities outside [0, 1] are rejected."""
    with pytest.raises(ValueError):
        generate_watts_strogatz(10, 4, -0.1)
    with pytest.raises(ValueError):
        generate_watts_strogatz(10, 4, 1.1)


def test_dispatch_erdos_renyi() -> None:
    """The dispatcher calls the correct generator."""
    request = GeneratorRequest(
        kind=GeneratorKind.ERDOS_RENYI,
        node_count=8,
        probability=1.0,
        seed=1,
    )
    graph = generate(request)
    assert graph.edge_count == 28


def test_dispatch_barabasi_albert() -> None:
    """The dispatcher calls the correct generator."""
    request = GeneratorRequest(
        kind=GeneratorKind.BARABASI_ALBERT,
        node_count=10,
        edges_per_new_node=2,
        seed=1,
    )
    graph = generate(request)
    assert graph.node_count == 10


def test_dispatch_watts_strogatz() -> None:
    """The dispatcher calls the correct generator."""
    request = GeneratorRequest(
        kind=GeneratorKind.WATTS_STROGATZ,
        node_count=10,
        neighbors_per_node=4,
        rewiring_probability=0.0,
        seed=1,
    )
    graph = generate(request)
    assert graph.edge_count == 20
