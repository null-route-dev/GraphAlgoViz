"""Prim's minimum spanning tree algorithm with step-by-step output."""

import heapq

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph


class PrimMST(BaseAlgorithm):
    """Prim's algorithm for the minimum spanning tree of an undirected graph.

    Starting from a given node, the algorithm grows the tree by
    repeatedly adding the cheapest edge that connects a node outside
    the tree to a node inside it. Each step adds exactly one node to
    the tree, or finishes when no more nodes can be reached.

    The algorithm works correctly on undirected graphs. Directed
    edges are traversed according to their direction, which may
    produce a non-optimal result. For a minimum spanning tree, use
    an undirected graph. Parallel edges are handled by
    ``Graph.weighted_neighbors``, which reports the smallest weight
    between two nodes.

    If the start node's connected component does not cover the whole
    graph, the algorithm stops when that component is fully spanned.
    Nodes outside it are not visited.

    Args:
        graph: The graph to process.
        start_node_id: Id of the node to start from.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._in_tree: set[int] = {start_node_id}
        self._tree_edges: set[tuple[int, int]] = set()
        self._edge_weights: dict[int, float] = {start_node_id: 0.0}
        self._heap: list[tuple[float, int, int]] = []
        self._finished = False

        for neighbor, weight in graph.weighted_neighbors(start_node_id):
            heapq.heappush(self._heap, (weight, start_node_id, neighbor))

        if not self._heap:
            self._finished = True

    @property
    def is_finished(self) -> bool:
        """Whether the tree has covered every reachable node.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    def step(self) -> StepResult:
        """Add the next node to the minimum spanning tree.

        Returns:
            A snapshot showing the nodes in the tree, the newly added
            node, the tree edges, and per-node connection weights.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        while self._heap:
            weight, source, target = heapq.heappop(self._heap)
            if target in self._in_tree:
                continue

            self._in_tree.add(target)
            self._tree_edges.add((source, target))
            self._edge_weights[target] = weight

            for neighbor, neighbor_weight in self._graph.weighted_neighbors(target):
                if neighbor not in self._in_tree:
                    heapq.heappush(
                        self._heap,
                        (neighbor_weight, target, neighbor),
                    )

            self._prune_stale_entries()

            if not self._heap:
                self._finished = True

            total_weight = sum(self._edge_weights.values())
            labels = {
                node_id: f"{value:g}" for node_id, value in self._edge_weights.items()
            }
            return StepResult(
                visited=frozenset(self._in_tree),
                current=target,
                frontier=(),
                tree_edges=frozenset(self._tree_edges),
                labels=labels,
                info=(
                    f"Added node {target} via edge weight {weight:g}, "
                    f"total {total_weight:g}"
                ),
            )

        self._finished = True
        raise RuntimeError("Algorithm already finished")

    def _prune_stale_entries(self) -> None:
        """Drop heap entries whose target is already in the tree."""
        while self._heap and self._heap[0][2] in self._in_tree:
            heapq.heappop(self._heap)
