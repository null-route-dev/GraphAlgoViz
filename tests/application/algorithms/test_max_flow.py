"""Tests for the Edmonds-Karp maximum flow algorithm."""

import pytest

from application.algorithms.max_flow import MaxFlow
from application.algorithms.step_result import StepResult
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_diamond() -> Graph:
    """Return a simple max-flow graph with a known answer.

    Structure: 1 -> 2 (cap 3), 1 -> 3 (cap 2), 2 -> 4 (cap 2),
    3 -> 4 (cap 3). Max flow from 1 to 4 is 4.
    """
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=3.0, directed=True))
    graph.add_edge(Edge(source=1, target=3, weight=2.0, directed=True))
    graph.add_edge(Edge(source=2, target=4, weight=2.0, directed=True))
    graph.add_edge(Edge(source=3, target=4, weight=3.0, directed=True))
    return graph


def build_chain() -> Graph:
    """Return a directed chain 1 -> 2 -> 3 with capacities 5 and 3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=5.0, directed=True))
    graph.add_edge(Edge(source=2, target=3, weight=3.0, directed=True))
    return graph


def build_no_path() -> Graph:
    """Return a graph where the sink is unreachable from the source."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, weight=5.0, directed=True))
    return graph


def run_to_completion(algorithm: MaxFlow) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_source_must_exist() -> None:
    """A missing source raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Source node 42"):
        MaxFlow(graph, source_id=42, sink_id=3)


def test_sink_must_exist() -> None:
    """A missing sink raises ValueError."""
    graph = build_chain()
    with pytest.raises(ValueError, match="Sink node 42"):
        MaxFlow(graph, source_id=1, sink_id=42)


def test_source_equals_sink() -> None:
    """Source equal to sink finishes immediately with zero flow."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=1)

    assert algorithm.is_finished is True
    assert algorithm.total_flow == 0.0


def test_simple_chain_flow() -> None:
    """A chain's max flow is the minimum capacity along it."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    run_to_completion(algorithm)

    assert algorithm.total_flow == 3.0


def test_diamond_max_flow() -> None:
    """A diamond reaches the expected max flow."""
    algorithm = MaxFlow(build_diamond(), source_id=1, sink_id=4)
    run_to_completion(algorithm)

    assert algorithm.total_flow == 4.0


def test_no_path_gives_zero_flow() -> None:
    """An unreachable sink gives zero flow."""
    algorithm = MaxFlow(build_no_path(), source_id=1, sink_id=3)
    run_to_completion(algorithm)

    assert algorithm.total_flow == 0.0


def test_flow_values_are_valid() -> None:
    """Every arc's flow lies between zero and its capacity."""
    graph = build_diamond()
    algorithm = MaxFlow(graph, source_id=1, sink_id=4)
    run_to_completion(algorithm)

    for edge in graph.edges():
        flow = algorithm.flow_on(edge.source, edge.target)
        capacity = algorithm.capacity_of(edge.source, edge.target)
        assert 0.0 <= flow <= capacity


def test_flow_conservation() -> None:
    """Incoming flow equals outgoing flow at every internal node."""
    graph = build_diamond()
    algorithm = MaxFlow(graph, source_id=1, sink_id=4)
    run_to_completion(algorithm)

    for node_id in (2, 3):
        incoming = sum(
            algorithm.flow_on(e.source, e.target)
            for e in graph.edges()
            if e.target == node_id
        )
        outgoing = sum(
            algorithm.flow_on(e.source, e.target)
            for e in graph.edges()
            if e.source == node_id
        )
        assert incoming == pytest.approx(outgoing)


def test_source_outflow_equals_total_flow() -> None:
    """The source's total outflow equals the total flow."""
    graph = build_diamond()
    algorithm = MaxFlow(graph, source_id=1, sink_id=4)
    run_to_completion(algorithm)

    outflow = sum(
        algorithm.flow_on(e.source, e.target) for e in graph.edges() if e.source == 1
    )
    assert outflow == pytest.approx(algorithm.total_flow)


def test_sink_inflow_equals_total_flow() -> None:
    """The sink's total inflow equals the total flow."""
    graph = build_diamond()
    algorithm = MaxFlow(graph, source_id=1, sink_id=4)
    run_to_completion(algorithm)

    inflow = sum(
        algorithm.flow_on(e.source, e.target) for e in graph.edges() if e.target == 4
    )
    assert inflow == pytest.approx(algorithm.total_flow)


def test_undirected_edge_is_bidirectional() -> None:
    """An undirected edge carries flow in both directions."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=5.0))

    algorithm = MaxFlow(graph, source_id=1, sink_id=2)
    run_to_completion(algorithm)

    assert algorithm.total_flow == 5.0
    assert algorithm.capacity_of(1, 2) == 5.0
    assert algorithm.capacity_of(2, 1) == 5.0


def test_edge_labels_use_flow_over_capacity() -> None:
    """Step results include edge labels in flow/capacity form."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    result = algorithm.step()

    assert (1, 2) in result.edge_labels
    assert "/" in result.edge_labels[(1, 2)]


def test_path_edges_are_reported() -> None:
    """The augmenting path edges are reported in tree_edges."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    result = algorithm.step()

    assert result.tree_edges == frozenset({(1, 2), (2, 3)})


def test_info_reports_augmentation() -> None:
    """Each augmentation step mentions the amount and total."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    result = algorithm.step()

    assert "Augmented" in result.info
    assert "total flow" in result.info


def test_final_step_reports_no_path() -> None:
    """The final step says no augmenting path remains."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    steps = run_to_completion(algorithm)

    assert "No augmenting path" in steps[-1].info


def test_step_count_for_chain() -> None:
    """A chain with uniform flow takes two steps."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    steps = run_to_completion(algorithm)

    assert len(steps) == 2


def test_parallel_edges_sum_capacities() -> None:
    """Parallel edges contribute their capacities together."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=3.0, directed=True))
    graph.add_edge(Edge(source=1, target=2, weight=4.0, directed=True))

    algorithm = MaxFlow(graph, source_id=1, sink_id=2)
    run_to_completion(algorithm)

    assert algorithm.total_flow == 7.0


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = MaxFlow(build_chain(), source_id=1, sink_id=3)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()
