"""A* shortest-path algorithm with step-by-step output."""

import heapq
from collections import deque

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class AStar(BaseAlgorithm):
    """A* shortest-path search using a distance-based heuristic.

    The heuristic estimates the remaining distance from a node to the
    target as the number of hops in the underlying unweighted graph
    multiplied by the smallest edge weight in the graph. This bound is
    admissible: any path from a node to the target must use at least
    that many edges, each of which weighs at least the minimum edge
    weight. It is also consistent, so no node is expanded twice with
    an improved distance.

    The heuristic treats the graph as undirected. For directed graphs
    the actual path may be longer, so the estimate remains admissible.

    Each step expands exactly one node. When the target is expanded,
    the algorithm stops and reports the final distance. If the target
    is unreachable, the algorithm explores every reachable node and
    then stops, reporting failure in the last step.

    Negative edge weights break the admissibility of the heuristic
    and produce incorrect results. The minimum edge weight is clamped
    to zero in that case, which keeps the algorithm correct but
    degrades it to Dijkstra.

    Args:
        graph: The graph to search.
        start_node_id: Id of the node to start from.
        target_node_id: Id of the node to reach.

    Raises:
        ValueError: If either node does not exist in the graph.
    """

    def __init__(
        self,
        graph: Graph,
        start_node_id: int,
        target_node_id: int,
    ) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")
        if not graph.has_node(target_node_id):
            raise ValueError(f"Target node {target_node_id} does not exist")

        self._graph = graph
        self._start = start_node_id
        self._target = target_node_id
        self._heuristic = self._compute_heuristic(graph, target_node_id)

        self._distances: dict[int, float] = {start_node_id: 0.0}
        self._parents: dict[int, int] = {}
        self._finalized: set[int] = set()
        self._queue: list[tuple[float, float, int]] = []
        heapq.heappush(
            self._queue,
            (self._heuristic_value(start_node_id), 0.0, start_node_id),
        )
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether the algorithm has stopped.

        Returns:
            True if the target was reached or the search exhausted.
        """
        return self._finished

    @property
    def target_reached(self) -> bool:
        """Whether the target has been finalized.

        Returns:
            True if the target was reached.
        """
        return self._target in self._finalized

    @property
    def distance_to_target(self) -> float | None:
        """Shortest distance to the target, if it was reached.

        Returns:
            The distance, or None if the target was not reached.
        """
        if not self.target_reached:
            return None
        return self._distances.get(self._target)

    def step(self) -> StepResult:
        """Expand the next node with the smallest estimated total cost.

        Returns:
            A snapshot showing finalized nodes, the node just
            expanded, the pending frontier sorted by f-value, tree
            edges, distance labels, and a description of the step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        current: int | None = None
        g_value = 0.0
        while self._queue:
            _, g_value, popped = heapq.heappop(self._queue)
            if popped not in self._finalized:
                current = popped
                break

        if current is None:
            self._finished = True
            return self._snapshot(
                None,
                f"Target {self._target} is unreachable from {self._start}",
            )

        self._finalized.add(current)

        if current == self._target:
            self._finished = True
            message = f"Reached target {self._target} with distance {g_value:g}"
            return self._snapshot(current, message)

        for neighbor, weight in self._graph.weighted_neighbors(current):
            if neighbor in self._finalized:
                continue
            candidate = g_value + weight
            if neighbor not in self._distances or candidate < self._distances[neighbor]:
                self._distances[neighbor] = candidate
                self._parents[neighbor] = current
                h_value = self._heuristic_value(neighbor)
                heapq.heappush(self._queue, (candidate + h_value, candidate, neighbor))

        h_value = self._heuristic_value(current)
        f_display = g_value + h_value
        message = (
            f"Expanded node {current} (g={g_value:g}, h={h_value:g}, f={f_display:g})"
        )
        return self._snapshot(current, message)

    def _snapshot(self, current: int | None, message: str) -> StepResult:
        pending = sorted(
            self._distances.keys() - self._finalized,
            key=lambda n: self._distances[n] + self._heuristic_value(n),
        )
        tree_edges = frozenset((parent, node) for node, parent in self._parents.items())
        labels = {nid: f"{d:g}" for nid, d in self._distances.items()}
        return StepResult(
            visited=frozenset(self._finalized),
            current=current,
            frontier=tuple(pending),
            tree_edges=tree_edges,
            labels=labels,
            info=message,
        )

    def _heuristic_value(self, node_id: int) -> float:
        return self._heuristic.get(node_id, 0.0)

    @staticmethod
    def _compute_heuristic(graph: Graph, target_id: int) -> dict[int, float]:
        adjacency: dict[int, list[int]] = {node.id: [] for node in graph.nodes()}
        for edge in graph.edges():
            adjacency[edge.source].append(edge.target)
            adjacency[edge.target].append(edge.source)

        hops: dict[int, int] = {target_id: 0}
        queue: deque[int] = deque([target_id])
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if neighbor not in hops:
                    hops[neighbor] = hops[node] + 1
                    queue.append(neighbor)

        weights = [edge.weight for edge in graph.edges()]
        min_weight = min(weights) if weights else 0.0
        min_weight = max(min_weight, 0.0)

        return {node_id: hop * min_weight for node_id, hop in hops.items()}
