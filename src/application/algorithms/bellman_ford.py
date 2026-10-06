"""Bellman-Ford shortest-path algorithm with step-by-step output."""

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class BellmanFord(BaseAlgorithm):
    """Single-source shortest paths on a graph with arbitrary weights.

    Bellman-Ford relaxes every edge repeatedly. Up to V-1 passes are
    needed to compute the shortest distances in the absence of
    negative cycles. If a pass makes no updates, distances are final
    and the algorithm stops early. After V-1 passes, one more pass is
    performed to detect negative cycles: if any edge can still be
    relaxed, a negative cycle is reachable from the start node.

    For undirected graphs, every edge is treated as two opposite
    directed edges. A negative-weight undirected edge therefore forms
    a negative cycle of length two, which the algorithm correctly
    detects. This is not a bug of the algorithm — it is the correct
    interpretation of undirected negative edges.

    Self-loops with negative weight are treated as negative cycles of
    length one. The UI does not create self-loops, so this case does
    not arise in practice. The algorithm handles it correctly anyway.

    Parallel edges are all considered independently, as the classical
    algorithm requires.

    Args:
        graph: The graph to search.
        start_node_id: Id of the node to start from.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        edges: list[tuple[int, int, float]] = []
        for edge in graph.edges():
            edges.append((edge.source, edge.target, edge.weight))
            if not edge.directed:
                edges.append((edge.target, edge.source, edge.weight))
        self._edges = edges

        self._distances: dict[int, float] = {start_node_id: 0.0}
        self._parents: dict[int, int] = {}
        self._num_relaxation_passes = max(0, graph.node_count - 1)
        self._pass_index = 0
        self._edge_index = 0
        self._updated_in_pass = False
        self._negative_cycle = False
        self._finished = not edges

    @property
    def is_finished(self) -> bool:
        """Whether the algorithm has run to completion.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    @property
    def has_negative_cycle(self) -> bool:
        """Whether a reachable negative cycle was detected.

        Returns:
            True if the last detection pass found a relaxation,
            indicating a negative cycle reachable from the start.
            Only meaningful after ``is_finished`` is True.
        """
        return self._negative_cycle

    @property
    def distances(self) -> dict[int, float]:
        """Current shortest distances from the start node.

        Returns:
            A copy of the mapping from node id to distance. Only
            nodes reached so far are included.
        """
        return dict(self._distances)

    def step(self) -> StepResult:
        """Process the next edge in the current pass.

        Returns:
            A snapshot showing reached nodes, the target of the
            current edge, tree edges from current parents, distance
            labels, and a description of the step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        source, target, weight = self._edges[self._edge_index]
        previous = self._distances.get(target)

        is_detection = self._pass_index >= self._num_relaxation_passes
        pass_label = "Detection" if is_detection else f"Pass {self._pass_index + 1}"
        edge_label = f"edge {source}->{target}"

        if source not in self._distances:
            message = f"{pass_label}: {edge_label}, source not reached"
        else:
            candidate = self._distances[source] + weight
            if previous is None or candidate < previous:
                self._distances[target] = candidate
                self._parents[target] = source
                self._updated_in_pass = True
                if previous is None:
                    message = (
                        f"{pass_label}: {edge_label}, dist[{target}] = {candidate:g}"
                    )
                else:
                    message = (
                        f"{pass_label}: {edge_label}, "
                        f"dist[{target}] {previous:g} -> {candidate:g}"
                    )
            else:
                message = f"{pass_label}: {edge_label}, no change"

        self._edge_index += 1
        at_end = self._edge_index >= len(self._edges)
        if at_end:
            self._edge_index = 0

        if at_end:
            if self._pass_index < self._num_relaxation_passes:
                if not self._updated_in_pass:
                    self._finished = True
                    message += " (converged)"
                else:
                    self._pass_index += 1
                    self._updated_in_pass = False
            else:
                if self._updated_in_pass:
                    self._negative_cycle = True
                    message += " (negative cycle detected)"
                else:
                    message += " (no negative cycle)"
                self._finished = True

        return StepResult(
            visited=frozenset(self._distances.keys()),
            current=target,
            frontier=(),
            tree_edges=frozenset(
                (parent, node) for node, parent in self._parents.items()
            ),
            labels={nid: f"{d:g}" for nid, d in self._distances.items()},
            info=message,
        )
