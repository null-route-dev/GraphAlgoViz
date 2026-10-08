"""Tests for Tarjan's strongly connected components algorithm."""

import pytest

from application.algorithms.step_result import StepResult
from application.algorithms.tarjan_scc import SCC_PALETTE, TarjanSCC
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def build_cycle() -> Graph:
    """Return a directed 3-cycle 1->2->3->1."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    graph.add_edge(Edge(source=3, target=1, directed=True))
    return graph


def build_chain() -> Graph:
    """Return a directed chain 1->2->3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    return graph


def build_two_cycles() -> Graph:
    """Return two disconnected cycles: {1,2} and {3,4}."""
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=1, directed=True))
    graph.add_edge(Edge(source=3, target=4, directed=True))
    graph.add_edge(Edge(source=4, target=3, directed=True))
    return graph


def build_cycle_with_outgoing() -> Graph:
    """Return a cycle {1,2} with an edge to an isolated node 3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=1, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    return graph


def build_nested_cycles() -> Graph:
    """Return a cycle 1-2 with a branch into cycle 3-4 with a back edge.

    Structure: 1 -> 2 -> 1 (cycle A)
               2 -> 3 -> 4 -> 3 (cycle B, entered from A)
    A and B are separate SCCs: no path returns from B to A.
    """
    graph = Graph()
    for node_id in (1, 2, 3, 4):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2, directed=True))
    graph.add_edge(Edge(source=2, target=1, directed=True))
    graph.add_edge(Edge(source=2, target=3, directed=True))
    graph.add_edge(Edge(source=3, target=4, directed=True))
    graph.add_edge(Edge(source=4, target=3, directed=True))
    return graph


def build_undirected_chain() -> Graph:
    """Return an undirected chain 1-2-3."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=1, target=2))
    graph.add_edge(Edge(source=2, target=3))
    return graph


def run_to_completion(algorithm: TarjanSCC) -> list[StepResult]:
    """Run the algorithm to completion and return all step results."""
    steps: list[StepResult] = []
    while not algorithm.is_finished:
        steps.append(algorithm.step())
    return steps


def test_start_node_must_exist() -> None:
    """A missing start node raises ValueError."""
    graph = build_cycle()
    with pytest.raises(ValueError, match="Start node 42"):
        TarjanSCC(graph, start_node_id=42)


def test_single_node_graph() -> None:
    """A single node is its own SCC."""
    graph = Graph()
    graph.add_node(Node(id=1))

    algorithm = TarjanSCC(graph, start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 1
    assert algorithm.sccs() == [[1]]


def test_three_cycle_is_one_scc() -> None:
    """A directed 3-cycle is a single SCC."""
    algorithm = TarjanSCC(build_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 1
    assert algorithm.sccs() == [[1, 2, 3]]


def test_chain_has_singleton_sccs() -> None:
    """A directed chain has one SCC per node."""
    algorithm = TarjanSCC(build_chain(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 3
    assert algorithm.sccs() == [[1], [2], [3]]


def test_two_disconnected_cycles() -> None:
    """Two disconnected 2-cycles form two SCCs."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 2
    assert algorithm.sccs() == [[1, 2], [3, 4]]


def test_cycle_with_outgoing_edge() -> None:
    """A cycle with an outgoing edge to an isolated node yields two SCCs."""
    algorithm = TarjanSCC(build_cycle_with_outgoing(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 2
    assert algorithm.sccs() == [[1, 2], [3]]


def test_nested_cycles_are_separate_sccs() -> None:
    """Two cycles connected by a one-way edge are separate SCCs."""
    algorithm = TarjanSCC(build_nested_cycles(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 2
    assert algorithm.sccs() == [[1, 2], [3, 4]]


def test_undirected_chain_is_one_scc() -> None:
    """An undirected chain behaves as a bidirectional path — one SCC."""
    algorithm = TarjanSCC(build_undirected_chain(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_count == 1
    assert algorithm.sccs() == [[1, 2, 3]]


def test_start_node_does_not_limit_processing() -> None:
    """Starting from node 1 still finds SCCs in disconnected parts."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_of(3) is not None
    assert algorithm.scc_of(4) is not None


def test_scc_of_returns_index() -> None:
    """Nodes in the same SCC share the same index."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    run_to_completion(algorithm)

    assert algorithm.scc_of(1) == algorithm.scc_of(2)
    assert algorithm.scc_of(3) == algorithm.scc_of(4)
    assert algorithm.scc_of(1) != algorithm.scc_of(3)


def test_colors_differ_between_sccs() -> None:
    """Different SCCs receive different fill colors."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    steps = run_to_completion(algorithm)
    colors = steps[-1].node_colors

    assert colors[1] == colors[2]
    assert colors[3] == colors[4]
    assert colors[1] != colors[3]


def test_colors_come_from_palette() -> None:
    """Every assigned color is drawn from the SCC palette."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    steps = run_to_completion(algorithm)

    for color in steps[-1].node_colors.values():
        assert color in SCC_PALETTE


def test_colors_only_for_completed_sccs() -> None:
    """Nodes not yet in a completed SCC have no explicit color."""
    algorithm = TarjanSCC(build_cycle(), start_node_id=1)
    first = algorithm.step()

    assert 1 not in first.node_colors


def test_frontier_holds_the_tarjan_stack() -> None:
    """Frontier contains the nodes on the Tarjan stack in order."""
    algorithm = TarjanSCC(build_chain(), start_node_id=1)
    first = algorithm.step()

    assert first.frontier == (1,)


def test_info_reports_scc_close() -> None:
    """The step that closes an SCC mentions it."""
    algorithm = TarjanSCC(build_chain(), start_node_id=1)
    steps = run_to_completion(algorithm)
    messages = [step.info for step in steps]

    assert any("Closed SCC" in msg for msg in messages)


def test_final_step_reports_scc_count() -> None:
    """The last step reports the number of SCCs found."""
    algorithm = TarjanSCC(build_two_cycles(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert "2 SCC" in steps[-1].info


def test_step_after_finish_raises() -> None:
    """Calling step after completion raises RuntimeError."""
    algorithm = TarjanSCC(build_cycle(), start_node_id=1)
    run_to_completion(algorithm)

    with pytest.raises(RuntimeError, match="already finished"):
        algorithm.step()


def test_info_mentions_lowlink_updates() -> None:
    """A back edge that updates lowlink is reported."""
    algorithm = TarjanSCC(build_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)
    messages = [step.info for step in steps]

    assert any("lowlink" in msg for msg in messages)


def test_step_count_matches_formula() -> None:
    """The number of steps equals R + V + E + 1."""
    algorithm = TarjanSCC(build_cycle(), start_node_id=1)
    steps = run_to_completion(algorithm)

    assert len(steps) == 8
