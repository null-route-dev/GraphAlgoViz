"""Greedy graph coloring with step-by-step output."""

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class GreedyColoring(BaseAlgorithm):
    """Greedy graph coloring.

    Colors are positive integers starting from 1. Nodes are processed
    one at a time. Each node receives the smallest color not used by
    any of its already-colored neighbors. Uncolored neighbors are not
    considered, which is what makes the algorithm greedy.

    The number of colors used is at most one more than the maximum
    degree of the graph, but the exact result depends on the order in
    which nodes are processed. Different orders can yield different
    numbers of colors.

    The starting node is colored first. The remaining nodes follow in
    the order they appear in the graph. This produces a deterministic
    result that does not depend on dictionary iteration order beyond
    what the graph itself exposes.

    For directed graphs, neighbors are only those reachable along an
    outgoing edge. Two nodes connected by a single directed edge may
    end up with the same color, because the coloring follows the
    direction of the edge.

    Args:
        graph: The graph to color.
        start_node_id: Id of the node to color first.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        order = [start_node_id]
        for node in graph.nodes():
            if node.id != start_node_id:
                order.append(node.id)
        self._order: list[int] = order
        self._index = 0
        self._colors: dict[int, int] = {}
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether every node has been colored.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    def step(self) -> StepResult:
        """Color the next node in the processing order.

        Returns:
            A snapshot showing colored nodes, the node just colored,
            the remaining nodes, and per-node color numbers.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        node_id = self._order[self._index]
        self._index += 1

        used: set[int] = set()
        for neighbor in self._graph.neighbors(node_id):
            if neighbor in self._colors:
                used.add(self._colors[neighbor])

        color = 1
        while color in used:
            color += 1
        self._colors[node_id] = color

        if self._index >= len(self._order):
            self._finished = True

        return StepResult(
            visited=frozenset(self._colors.keys()),
            current=node_id,
            frontier=tuple(self._order[self._index :]),
            tree_edges=frozenset(),
            labels={nid: str(c) for nid, c in self._colors.items()},
            info=f"Colored node {node_id} with color {color}",
        )
