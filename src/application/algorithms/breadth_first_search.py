"""Iterative breadth-first search with step-by-step output."""

from collections import deque

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class BreadthFirstSearch(BaseAlgorithm):
    """Breadth-first traversal starting from a given node.

    The algorithm uses a FIFO queue so that nodes are visited in order
    of their distance from the start: all neighbours of the start first,
    then their neighbours, and so on.

    A node is never enqueued twice. This keeps the number of visible
    steps equal to the number of visited nodes.

    Args:
        graph: The graph to traverse.
        start_node_id: Id of the node to start from.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._visited: set[int] = set()
        self._queue: deque[int] = deque([start_node_id])
        self._pending: set[int] = {start_node_id}
        self._tree_edges: set[tuple[int, int]] = set()
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether the traversal has completed.

        Returns:
            True if every reachable node has been visited.
        """
        return self._finished

    def step(self) -> StepResult:
        """Process the next node in the queue.

        Returns:
            A snapshot showing the new visited set, the current node,
            the remaining queue, and the traversal tree edges.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        current = self._queue.popleft()
        self._pending.discard(current)
        self._visited.add(current)

        for neighbor in self._graph.neighbors(current):
            if neighbor in self._visited or neighbor in self._pending:
                continue
            self._queue.append(neighbor)
            self._pending.add(neighbor)
            self._tree_edges.add((current, neighbor))

        if not self._queue:
            self._finished = True

        return StepResult(
            visited=frozenset(self._visited),
            current=current,
            frontier=tuple(self._queue),
            tree_edges=frozenset(self._tree_edges),
            info=f"Visited node {current}",
        )
