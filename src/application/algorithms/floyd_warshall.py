"""Floyd-Warshall all-pairs shortest-path algorithm."""

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

INFINITY_LABEL = "∞"


class FloydWarshall(BaseAlgorithm):
    """All-pairs shortest paths on a graph with arbitrary weights.

    The algorithm computes distances between every pair of nodes by
    considering each node in turn as an intermediate point on the
    shortest path. For each intermediate node k and each pair (i, j),
    the distance d[i][j] is replaced by d[i][k] + d[k][j] if that is
    shorter.

    Each step considers exactly one triple (k, i, j). The info string
    describes what happened to d[i][j], and the matrix snapshot shows
    the current state of all distances. The cell (i, j) is marked as
    the current cell, and the row and column of k are emphasized by
    the UI.

    The starting node id is accepted for interface compatibility with
    the algorithm registry. The algorithm itself computes all pairs,
    so the value is only used to validate that the graph contains the
    node. It does not affect the result.

    Negative edges are supported. Negative cycles make some distances
    undefined and produce negative values along the diagonal, but the
    algorithm still completes. Detecting negative cycles is the job
    of Bellman-Ford, not of this algorithm.

    Args:
        graph: The graph to search.
        start_node_id: Id of an existing node, used only for
            validation.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._node_ids: list[int] = [node.id for node in graph.nodes()]
        self._dist: dict[tuple[int, int], float] = {
            (nid, nid): 0.0 for nid in self._node_ids
        }
        for edge in graph.edges():
            self._update_initial_distance(edge.source, edge.target, edge.weight)
            if not edge.directed:
                self._update_initial_distance(edge.target, edge.source, edge.weight)

        self._k_index = 0
        self._i_index = 0
        self._j_index = 0
        self._finished = False

        if not self._node_ids:
            self._finished = True

    @property
    def is_finished(self) -> bool:
        """Whether every triple (k, i, j) has been processed.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    def distance(self, from_id: int, to_id: int) -> float | None:
        """Return the shortest distance between two nodes.

        Args:
            from_id: Id of the source node.
            to_id: Id of the target node.

        Returns:
            The shortest distance, or None if the nodes are not yet
            connected by any path or are not in the graph.
        """
        return self._dist.get((from_id, to_id))

    def step(self) -> StepResult:
        """Consider the next triple (k, i, j).

        Returns:
            A snapshot showing the matrix of distances, the cell
            being considered, the current intermediate node, and a
            description of the step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        k_id = self._node_ids[self._k_index]
        i_id = self._node_ids[self._i_index]
        j_id = self._node_ids[self._j_index]

        message = self._relax(k_id, i_id, j_id)

        self._advance()

        return StepResult(
            visited=frozenset(self._node_ids[: self._k_index]),
            current=k_id,
            info=message,
            matrix=self._build_matrix(),
            highlight_cell=(i_id, j_id),
        )

    def _update_initial_distance(
        self,
        source: int,
        target: int,
        weight: float,
    ) -> None:
        key = (source, target)
        existing = self._dist.get(key)
        if existing is None or weight < existing:
            self._dist[key] = weight

    def _relax(self, k_id: int, i_id: int, j_id: int) -> str:
        ik = self._dist.get((i_id, k_id))
        kj = self._dist.get((k_id, j_id))
        ij = self._dist.get((i_id, j_id))

        if i_id == j_id:
            return f"k={k_id}: d[{i_id}][{j_id}] = 0"

        if ik is None or kj is None:
            return f"k={k_id}: d[{i_id}][{j_id}] no path via {k_id}"

        candidate = ik + kj
        if ij is None or candidate < ij:
            self._dist[(i_id, j_id)] = candidate
            if ij is None:
                return f"k={k_id}: d[{i_id}][{j_id}] = {candidate:g} (new)"
            return f"k={k_id}: d[{i_id}][{j_id}] = {candidate:g} (was {ij:g})"

        if ij is not None:
            return f"k={k_id}: d[{i_id}][{j_id}] unchanged ({ij:g})"
        return f"k={k_id}: d[{i_id}][{j_id}] unchanged"

    def _advance(self) -> None:
        count = len(self._node_ids)
        self._j_index += 1
        if self._j_index >= count:
            self._j_index = 0
            self._i_index += 1
        if self._i_index >= count:
            self._i_index = 0
            self._k_index += 1
        if self._k_index >= count:
            self._finished = True

    def _build_matrix(self) -> dict[tuple[int, int], str]:
        matrix: dict[tuple[int, int], str] = {}
        for i in self._node_ids:
            for j in self._node_ids:
                value = self._dist.get((i, j))
                if value is None:
                    matrix[(i, j)] = INFINITY_LABEL
                else:
                    matrix[(i, j)] = f"{value:g}"
        return matrix
