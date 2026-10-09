"""Edmonds-Karp maximum flow algorithm."""

from collections import deque

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class MaxFlow(BaseAlgorithm):
    """Edmonds-Karp maximum flow from a source to a sink.

    The algorithm repeatedly finds the shortest augmenting path in the
    residual graph using BFS, and pushes the maximum possible amount of
    flow along it. When no augmenting path remains, the total flow from
    the source is maximum.

    Edge weights are interpreted as capacities. Undirected edges are
    treated as two directed arcs, each with the same capacity, which
    is the standard interpretation for undirected maximum flow.

    Parallel edges between the same ordered pair of nodes have their
    capacities summed, since the algorithm operates on the aggregate
    capacity between pairs. The visualization also shows the summed
    value on each of the parallel edges.

    Each visible step corresponds to one augmenting path: the BFS
    finds a path, the bottleneck is computed, and flow is pushed along
    the path. The path's edges are reported via ``tree_edges`` so the
    canvas can highlight them. A final step reports the total flow
    when no more augmenting paths exist.

    Self-loops carry no useful flow and are ignored.

    Args:
        graph: The graph to process.
        source_id: Id of the source node.
        sink_id: Id of the sink node.

    Raises:
        ValueError: If either node does not exist in the graph.
    """

    def __init__(
        self,
        graph: Graph,
        source_id: int,
        sink_id: int,
    ) -> None:
        if not graph.has_node(source_id):
            raise ValueError(f"Source node {source_id} does not exist")
        if not graph.has_node(sink_id):
            raise ValueError(f"Sink node {sink_id} does not exist")

        self._graph = graph
        self._source = source_id
        self._sink = sink_id

        self._capacity: dict[tuple[int, int], float] = {}
        for edge in graph.edges():
            if edge.source == edge.target:
                continue
            self._add_capacity(edge.source, edge.target, edge.weight)
            if not edge.directed:
                self._add_capacity(edge.target, edge.source, edge.weight)

        self._flow: dict[tuple[int, int], float] = {}
        self._total_flow = 0.0
        self._finished = source_id == sink_id or not self._capacity

    @property
    def is_finished(self) -> bool:
        """Whether no augmenting path remains.

        Returns:
            True if the algorithm has run to completion.
        """
        return self._finished

    @property
    def total_flow(self) -> float:
        """Total flow pushed from source to sink so far.

        Returns:
            The total flow value.
        """
        return self._total_flow

    def flow_on(self, source: int, target: int) -> float:
        """Return the current flow on the arc source -> target.

        Args:
            source: Source node id.
            target: Target node id.

        Returns:
            The flow value, or 0.0 if no flow is present.
        """
        return self._flow.get((source, target), 0.0)

    def capacity_of(self, source: int, target: int) -> float:
        """Return the capacity of the arc source -> target.

        Args:
            source: Source node id.
            target: Target node id.

        Returns:
            The capacity, or 0.0 if the arc does not exist.
        """
        return self._capacity.get((source, target), 0.0)

    def step(self) -> StepResult:
        """Find an augmenting path and push flow along it.

        Returns:
            A snapshot showing the current flows on every edge, the
            edges of the augmenting path, and a description of the
            step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        path, bottleneck = self._find_augmenting_path()
        if path is None or bottleneck <= 0.0:
            self._finished = True
            return self._make_result(
                None,
                frozenset(),
                f"No augmenting path; total flow = {self._total_flow:g}",
            )

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            self._push(u, v, bottleneck)
        self._total_flow += bottleneck

        path_edges = frozenset((path[i], path[i + 1]) for i in range(len(path) - 1))
        path_label = " \u2192 ".join(str(n) for n in path)
        return self._make_result(
            path[-1],
            path_edges,
            f"Augmented {bottleneck:g} along {path_label}; "
            f"total flow = {self._total_flow:g}",
        )

    def _add_capacity(self, u: int, v: int, c: float) -> None:
        self._capacity[(u, v)] = self._capacity.get((u, v), 0.0) + c

    def _residual(self, u: int, v: int) -> float:
        cap = self._capacity.get((u, v), 0.0)
        fwd = self._flow.get((u, v), 0.0)
        bwd = self._flow.get((v, u), 0.0)
        return cap - fwd + bwd

    def _push(self, u: int, v: int, amount: float) -> None:
        reverse = self._flow.get((v, u), 0.0)
        cancel = min(reverse, amount)
        self._flow[(v, u)] = reverse - cancel
        remainder = amount - cancel
        if remainder > 0.0:
            self._flow[(u, v)] = self._flow.get((u, v), 0.0) + remainder

    def _find_augmenting_path(
        self,
    ) -> tuple[list[int] | None, float]:
        parent: dict[int, int] = {self._source: self._source}
        queue: deque[int] = deque([self._source])
        while queue:
            u = queue.popleft()
            if u == self._sink:
                break
            for v in self._residual_neighbors(u):
                if v not in parent:
                    parent[v] = u
                    queue.append(v)
        if self._sink not in parent:
            return None, 0.0

        path: list[int] = []
        current = self._sink
        while current != self._source:
            path.append(current)
            current = parent[current]
        path.append(self._source)
        path.reverse()

        bottleneck = float("inf")
        for i in range(len(path) - 1):
            residual = self._residual(path[i], path[i + 1])
            bottleneck = min(bottleneck, residual)
        return path, bottleneck

    def _residual_neighbors(self, u: int) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for a, b in self._capacity:
            if a != u or b in seen:
                continue
            if self._residual(a, b) > 0.0:
                result.append(b)
                seen.add(b)
        for a, b in self._flow:
            if b != u or a in seen:
                continue
            if self._flow.get((a, b), 0.0) > 0.0 and self._residual(b, a) > 0.0:
                result.append(a)
                seen.add(a)
        return result

    def _make_result(
        self,
        current: int | None,
        path_edges: frozenset[tuple[int, int]],
        message: str,
    ) -> StepResult:
        edge_labels: dict[tuple[int, int], str] = {}
        for edge in self._graph.edges():
            if edge.source == edge.target:
                continue
            cap = edge.weight
            fwd = self._flow.get((edge.source, edge.target), 0.0)
            bwd = self._flow.get((edge.target, edge.source), 0.0)
            net = fwd - bwd
            edge_labels[(edge.source, edge.target)] = f"{net:g}/{cap:g}"
        return StepResult(
            visited=frozenset(),
            current=current,
            frontier=(),
            tree_edges=path_edges,
            edge_labels=edge_labels,
            info=message,
        )
