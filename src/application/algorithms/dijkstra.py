"""Dijkstra shortest-path algorithm with step-by-step output."""

import heapq

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class Dijkstra(BaseAlgorithm):
    """Single-source shortest paths on a graph with non-negative weights.

    Each step finalizes one node: the one with the smallest tentative
    distance. Once finalized, a node's distance is final. The algorithm
    relaxes outgoing edges and updates tentative distances accordingly.

    Parallel edges are handled by ``Graph.weighted_neighbors``, which
    reports the smallest weight between two nodes.

    The algorithm assumes all edge weights are non-negative. Negative
    weights produce incorrect results. This is documented rather than
    validated to avoid an extra pass over the edges at construction.

    Args:
        graph: The graph to search.
        start_node_id: Id of the node to start from.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._start = start_node_id

        self._distances: dict[int, float] = {start_node_id: 0.0}
        self._parents: dict[int, int] = {}
        self._finalized: set[int] = set()
        self._pending: set[int] = {start_node_id}
        self._queue: list[tuple[float, int]] = [(0.0, start_node_id)]
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether the algorithm has finalized every reachable node.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    def step(self) -> StepResult:
        """Finalize the next node with the smallest tentative distance.

        Returns:
            A snapshot showing finalized nodes, the current node, the
            pending frontier sorted by distance, tree edges, and the
            distance labels for every node reached so far.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        distance, current = heapq.heappop(self._queue)
        self._pending.discard(current)
        self._finalized.add(current)

        for neighbor, weight in self._graph.weighted_neighbors(current):
            if neighbor in self._finalized:
                continue
            candidate = distance + weight
            if neighbor not in self._distances or candidate < self._distances[neighbor]:
                self._distances[neighbor] = candidate
                self._parents[neighbor] = current
                self._pending.add(neighbor)
                heapq.heappush(self._queue, (candidate, neighbor))

        self._prune_stale_entries()

        if not self._queue:
            self._finished = True

        labels = {node_id: f"{value:g}" for node_id, value in self._distances.items()}
        tree_edges = frozenset((parent, node) for node, parent in self._parents.items())
        frontier = tuple(
            sorted(self._pending, key=lambda node_id: self._distances[node_id])
        )

        return StepResult(
            visited=frozenset(self._finalized),
            current=current,
            frontier=frontier,
            tree_edges=tree_edges,
            labels=labels,
            info=f"Finalized node {current} at distance {distance:g}",
        )

    def _prune_stale_entries(self) -> None:
        """Drop heap entries whose node is already finalized."""
        while self._queue and self._queue[0][1] in self._finalized:
            heapq.heappop(self._queue)
