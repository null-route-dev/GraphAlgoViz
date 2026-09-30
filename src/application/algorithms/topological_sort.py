"""Topological sort with step-by-step output."""

from collections import deque

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class TopologicalSort(BaseAlgorithm):
    """Topological sort of a directed acyclic graph using Kahn's algorithm.

    The algorithm processes nodes with no incoming edges, one at a
    time. When a node is processed, it is appended to the sorted
    order, and the incoming counts of its outgoing neighbors are
    decremented. Neighbors whose count reaches zero become available
    for the next steps.

    Only directed edges are considered. Undirected edges are ignored,
    which makes the algorithm well-defined on mixed graphs but means
    the result does not reflect undirected connections. For a meaningful
    topological order, the graph should be directed and acyclic.

    If the graph contains a cycle among directed edges, the algorithm
    finishes with some nodes left unsorted. The last step reports this
    in its info string.

    Args:
        graph: The graph to sort.
        start_node_id: Id of a node to include in the sort. Accepted
            for interface compatibility; the algorithm always produces
            a complete topological order regardless of the starting
            point.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._outgoing: dict[int, list[int]] = {node.id: [] for node in graph.nodes()}
        self._in_degree: dict[int, int] = {node.id: 0 for node in graph.nodes()}
        for edge in graph.edges():
            if not edge.directed:
                continue
            self._outgoing[edge.source].append(edge.target)
            self._in_degree[edge.target] += 1

        self._queue: deque[int] = deque(
            nid for nid, degree in self._in_degree.items() if degree == 0
        )
        self._order: list[int] = []
        self._finished = False

        if not self._queue:
            self._finished = True

    @property
    def is_finished(self) -> bool:
        """Whether no more nodes can be added to the sorted order.

        Returns:
            True if the queue is empty.
        """
        return self._finished

    def step(self) -> StepResult:
        """Add the next available node to the sorted order.

        Returns:
            A snapshot showing sorted nodes, the node just added, the
            remaining queue, and per-node positions in the order.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        node_id = self._queue.popleft()
        self._order.append(node_id)

        for neighbor in self._outgoing[node_id]:
            self._in_degree[neighbor] -= 1
            if self._in_degree[neighbor] == 0:
                self._queue.append(neighbor)

        if not self._queue:
            self._finished = True

        position = len(self._order)
        unsorted = self._graph.node_count - position
        if self._finished and unsorted > 0:
            info = (
                f"Sorted node {node_id} (position {position}); "
                f"cycle detected, {unsorted} node(s) left unsorted"
            )
        else:
            info = f"Sorted node {node_id} (position {position})"

        return StepResult(
            visited=frozenset(self._order),
            current=node_id,
            frontier=tuple(self._queue),
            tree_edges=frozenset(),
            labels={nid: str(i + 1) for i, nid in enumerate(self._order)},
            info=info,
        )
