"""Traveling salesman via nearest neighbor and 2-opt."""

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

IMPROVEMENT_EPSILON = 1e-9

PHASE_NEAREST_NEIGHBOR = "nn"
PHASE_TWO_OPT = "2opt"
PHASE_DONE = "done"


class TravelingSalesman(BaseAlgorithm):
    """Approximate TSP using nearest neighbor and 2-opt.

    The algorithm has two phases. In the nearest neighbor phase, it
    starts at the given node and repeatedly visits the closest
    unvisited node, until no unvisited node remains. In the 2-opt
    phase, it repeatedly tries to replace two crossing edges with two
    cheaper ones, restarting after each improvement.

    Both phases are heuristics: the result is a valid tour but not
    necessarily optimal. The final tour length is at most that of the
    nearest neighbor tour, and typically smaller.

    If a node has no edge to any other node, the nearest neighbor
    phase stops early and the tour covers only the reachable nodes.
    Directed edges are treated as undirected for the purposes of the
    tour. Parallel edges are collapsed into the minimum weight between
    the same pair of nodes.

    Args:
        graph: The graph to traverse.
        start_node_id: Id of the node to start from.

    Raises:
        ValueError: If the start node does not exist.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        weights: dict[tuple[int, int], float] = {}
        for edge in graph.edges():
            if edge.source == edge.target:
                continue
            key = (
                min(edge.source, edge.target),
                max(edge.source, edge.target),
            )
            existing = weights.get(key)
            if existing is None or edge.weight < existing:
                weights[key] = edge.weight
        self._weights = weights

        all_nodes = [node.id for node in graph.nodes()]
        self._start = start_node_id
        self._tour: list[int] = [start_node_id]
        self._unvisited: set[int] = set(all_nodes) - {start_node_id}
        self._tour_edges: set[tuple[int, int]] = set()
        self._phase = PHASE_NEAREST_NEIGHBOR
        self._opt_i = 0
        self._opt_j = 2
        self._finished = len(all_nodes) < 2

    @property
    def is_finished(self) -> bool:
        """Whether both phases have completed.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    def tour(self) -> list[int]:
        """Return the current tour as a list of node ids.

        Returns:
            The tour order, starting from the initial node.
        """
        return list(self._tour)

    def tour_length(self) -> float:
        """Return the total length of the current tour.

        Returns:
            The sum of edge weights along the closed tour, or
            infinity if any edge is missing.
        """
        if len(self._tour) < 2:
            return 0.0
        total = 0.0
        count = len(self._tour)
        for i in range(count):
            u = self._tour[i]
            v = self._tour[(i + 1) % count]
            total += self._edge_weight(u, v)
        return total

    def step(self) -> StepResult:
        """Advance the algorithm by one action.

        Returns:
            A snapshot of the current state.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        if self._phase == PHASE_NEAREST_NEIGHBOR:
            return self._step_nearest_neighbor()
        if self._phase == PHASE_TWO_OPT:
            return self._step_two_opt()
        return self._make_result(None, None, "Algorithm complete")

    def _step_nearest_neighbor(self) -> StepResult:
        if not self._unvisited:
            return self._close_tour()

        current = self._tour[-1]
        best_node: int | None = None
        best_distance = float("inf")
        for candidate in sorted(self._unvisited):
            distance = self._edge_weight(current, candidate)
            if distance < best_distance:
                best_distance = distance
                best_node = candidate

        if best_node is None:
            self._finished = True
            self._phase = PHASE_DONE
            return self._make_result(
                current,
                None,
                "No reachable neighbor, tour incomplete",
            )

        self._unvisited.discard(best_node)
        self._tour.append(best_node)
        self._add_edge(current, best_node)
        return self._make_result(
            current,
            (current, best_node),
            f"Added node {best_node} at distance {best_distance:g}",
        )

    def _close_tour(self) -> StepResult:
        if len(self._tour) < 2:
            self._finished = True
            self._phase = PHASE_DONE
            return self._make_result(
                self._tour[0],
                None,
                "Single-node tour, nothing to close",
            )
        first = self._tour[0]
        last = self._tour[-1]
        if not self._has_edge(last, first):
            self._finished = True
            self._phase = PHASE_DONE
            return self._make_result(last, None, "Cannot close tour, edge missing")
        self._add_edge(last, first)
        self._phase = PHASE_TWO_OPT
        return self._make_result(
            last,
            (last, first),
            f"Closed tour, length {self.tour_length():g}",
        )

    def _step_two_opt(self) -> StepResult:
        count = len(self._tour)
        if count < 4:
            self._finished = True
            self._phase = PHASE_DONE
            return self._make_result(None, None, "Tour too short for 2-opt")

        while True:
            if self._opt_i >= count - 1:
                self._finished = True
                self._phase = PHASE_DONE
                return self._make_result(
                    None,
                    None,
                    f"2-opt complete, final length {self.tour_length():g}",
                )
            if self._opt_j >= count:
                self._opt_i += 1
                self._opt_j = self._opt_i + 2
                continue
            if self._opt_i == 0 and self._opt_j == count - 1:
                self._opt_j += 1
                continue
            break

        i = self._opt_i
        j = self._opt_j
        a = self._tour[i]
        b = self._tour[i + 1]
        c = self._tour[j]
        d = self._tour[(j + 1) % count]

        old_distance = self._edge_weight(a, b) + self._edge_weight(c, d)
        new_distance = self._edge_weight(a, c) + self._edge_weight(b, d)

        if new_distance < old_distance - IMPROVEMENT_EPSILON:
            self._tour[i + 1 : j + 1] = reversed(self._tour[i + 1 : j + 1])
            self._remove_edge(a, b)
            self._remove_edge(c, d)
            self._add_edge(a, c)
            self._add_edge(b, d)
            self._opt_i = 0
            self._opt_j = 2
            return self._make_result(
                a,
                (a, c),
                f"2-opt improved {old_distance:g} -> {new_distance:g}",
            )

        self._opt_j += 1
        return self._make_result(
            a,
            (a, b),
            f"2-opt ({i}, {j}): no improvement",
        )

    def _edge_weight(self, u: int, v: int) -> float:
        key = (min(u, v), max(u, v))
        return self._weights.get(key, float("inf"))

    def _has_edge(self, u: int, v: int) -> bool:
        return (min(u, v), max(u, v)) in self._weights

    def _add_edge(self, u: int, v: int) -> None:
        self._tour_edges.add((min(u, v), max(u, v)))

    def _remove_edge(self, u: int, v: int) -> None:
        self._tour_edges.discard((min(u, v), max(u, v)))

    def _make_result(
        self,
        current: int | None,
        current_edge: tuple[int, int] | None,
        message: str,
    ) -> StepResult:
        labels = {
            node_id: str(position + 1) for position, node_id in enumerate(self._tour)
        }
        return StepResult(
            current=current,
            current_edge=current_edge,
            tree_edges=frozenset(self._tour_edges),
            labels=labels,
            info=message,
        )
