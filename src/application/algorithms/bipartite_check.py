"""Bipartite check via iterative 2-coloring."""

from collections import deque

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

COLOR_A = "#4e79a7"
COLOR_B = "#f28e2b"


class BipartiteCheck(BaseAlgorithm):
    """Checks whether the graph is bipartite using 2-coloring.

    A graph is bipartite when its nodes can be split into two disjoint
    sets such that every edge has one endpoint in each set. This is
    equivalent to being 2-colorable: assign colors A and B to the two
    sets; every edge then connects an A node to a B node.

    The algorithm performs a breadth-first traversal from every
    unvisited node. Each newly discovered node receives the opposite
    color of the node it was discovered from. If an edge is found
    whose endpoints have the same color, the graph is not bipartite
    and the algorithm stops immediately.

    Directed edges are treated as undirected for the purpose of
    bipartiteness: only the presence or absence of an edge between
    two nodes matters, not its direction. The algorithm therefore
    works on the underlying undirected graph.

    A graph with multiple connected components is bipartite if and
    only if every component is bipartite. Each component is colored
    independently.

    Args:
        graph: The graph to check.
        start_node_id: Id of an existing node, used only for
            validation. The algorithm processes the whole graph.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._node_order: list[int] = [node.id for node in graph.nodes()]

        adjacency: dict[int, list[int]] = {node.id: [] for node in graph.nodes()}
        seen: set[tuple[int, int]] = set()
        for edge in graph.edges():
            if edge.source == edge.target:
                continue
            key = (min(edge.source, edge.target), max(edge.source, edge.target))
            if key in seen:
                continue
            seen.add(key)
            adjacency[edge.source].append(edge.target)
            adjacency[edge.target].append(edge.source)
        self._adjacency = adjacency

        self._color: dict[int, str] = {}
        self._next_root_pos = 0
        self._queue: deque[int] = deque()
        self._finished = False
        self._bipartite = True
        self._conflict_edge: tuple[int, int] | None = None

    @property
    def is_finished(self) -> bool:
        """Whether the whole graph has been processed or a conflict found.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    @property
    def is_bipartite(self) -> bool:
        """Whether the graph was determined to be bipartite.

        Returns:
            True if no conflict edge was found.
        """
        return self._bipartite

    @property
    def conflict_edge(self) -> tuple[int, int] | None:
        """The edge that broke bipartiteness, if any.

        Returns:
            The (source, target) pair of the offending edge, or None.
        """
        return self._conflict_edge

    def color_of(self, node_id: int) -> str | None:
        """Return the color assigned to a node.

        Args:
            node_id: Identifier of the node.

        Returns:
            The color string, or None if the node is not visited.
        """
        return self._color.get(node_id)

    def step(self) -> StepResult:
        """Process the next node or edge.

        Returns:
            A snapshot of the current state.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        if not self._queue:
            return self._start_next_component()

        node = self._queue.popleft()
        for neighbor in self._adjacency[node]:
            if neighbor in self._color:
                if self._color[neighbor] == self._color[node]:
                    self._bipartite = False
                    self._conflict_edge = (node, neighbor)
                    self._finished = True
                    return self._make_result(
                        node,
                        f"Conflict: {node} and {neighbor} share color",
                    )
                continue
            self._color[neighbor] = self._opposite(self._color[node])
            self._queue.append(neighbor)

        if not self._queue:
            remaining = any(nid not in self._color for nid in self._node_order)
            if not remaining:
                self._finished = True
                return self._make_result(node, "Graph is bipartite")

        return self._make_result(node, f"Processed node {node}")

    def _start_next_component(self) -> StepResult:
        while self._next_root_pos < len(self._node_order):
            root = self._node_order[self._next_root_pos]
            self._next_root_pos += 1
            if root in self._color:
                continue
            self._color[root] = COLOR_A
            self._queue.append(root)
            return self._make_result(root, f"New component, root {root}")
        self._finished = True
        return self._make_result(
            None,
            "Graph is bipartite" if self._bipartite else "Graph is not bipartite",
        )

    def _make_result(self, current: int | None, message: str) -> StepResult:
        conflict_edges: frozenset[tuple[int, int]] = (
            frozenset({self._conflict_edge})
            if self._conflict_edge is not None
            else frozenset()
        )
        return StepResult(
            visited=frozenset(self._color.keys()),
            current=current,
            frontier=tuple(self._queue),
            tree_edges=conflict_edges,
            node_colors=dict(self._color),
            info=message,
        )

    @staticmethod
    def _opposite(color: str) -> str:
        return COLOR_B if color == COLOR_A else COLOR_A
