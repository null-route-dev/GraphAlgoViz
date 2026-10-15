"""Maximum bipartite matching via Kuhn's algorithm."""

from collections import deque
from dataclasses import dataclass

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

MATCHED_COLOR = "#2ca02c"
ON_PATH_COLOR = "#d62728"


@dataclass
class _Frame:
    """One active DFS frame in Kuhn's augmenting path search.

    Args:
        left: Id of the left-partition node in this frame.
        neighbors: Right-partition neighbors, materialized once.
        next_index: Index of the next neighbor to consider.
    """

    left: int
    neighbors: list[int]
    next_index: int = 0


class BipartiteMatching(BaseAlgorithm):
    """Maximum bipartite matching using Kuhn's algorithm.

    The graph must be bipartite. The algorithm splits the nodes into
    left and right partitions using two-coloring, then searches for
    augmenting paths from each unmatched left node. Each search is a
    depth-first traversal that alternates between unmatched edges and
    matched edges. When an unmatched right node is reached, the path
    is augmented, growing the matching by one edge.

    The algorithm terminates when no augmenting path remains, at which
    point the matching is maximum. This is a consequence of Berge's
    theorem: a matching is maximum if and only if it admits no
    augmenting path.

    Edges within the same partition and self-loops are ignored: they
    cannot participate in a bipartite matching. Parallel edges between
    the same left and right node are collapsed into a single possible
    match.

    Args:
        graph: The graph to analyze. Must be bipartite.
        start_node_id: Id of an existing node, used only for
            validation. The algorithm processes the whole graph.

    Raises:
        ValueError: If the start node does not exist, or if the graph
            is not bipartite.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        left, right = _partition(graph)
        self._left: set[int] = left
        self._right: set[int] = right

        adjacency: dict[int, list[int]] = {u: [] for u in left}
        for edge in graph.edges():
            if edge.source in left and edge.target in right:
                adjacency[edge.source].append(edge.target)
            elif edge.target in left and edge.source in right:
                adjacency[edge.target].append(edge.source)
        self._adjacency = adjacency

        self._left_order: list[int] = sorted(left)
        self._matches: dict[int, int] = {}
        self._left_matched: dict[int, int] = {}

        self._next_left_index = 0
        self._dfs_stack: list[_Frame] = []
        self._visited_right: set[int] = set()
        self._path_edges: list[tuple[int, int]] = []
        self._finished = not self._left_order

    @property
    def is_finished(self) -> bool:
        """Whether no augmenting path remains.

        Returns:
            True if the matching is maximum.
        """
        return self._finished

    def matching_size(self) -> int:
        """Return the size of the current matching.

        Returns:
            The number of matched edges.
        """
        return len(self._matches)

    def matched_pairs(self) -> list[tuple[int, int]]:
        """Return the matched (left, right) pairs, sorted.

        Returns:
            A list of (left, right) pairs sorted by left id.
        """
        return sorted(self._left_matched.items())

    def step(self) -> StepResult:
        """Advance the algorithm by one action.

        Returns:
            A snapshot of the current state.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        if not self._dfs_stack:
            return self._start_next_search()
        return self._process_frame()

    def _start_next_search(self) -> StepResult:
        while self._next_left_index < len(self._left_order):
            root = self._left_order[self._next_left_index]
            self._next_left_index += 1
            if root in self._left_matched:
                continue
            self._dfs_stack.append(_Frame(root, list(self._adjacency[root])))
            self._visited_right.clear()
            self._path_edges.clear()
            return self._make_result(
                root, None, f"Searching for augmenting path from {root}"
            )
        self._finished = True
        return self._make_result(
            None,
            None,
            f"Maximum matching size = {self.matching_size()}",
        )

    def _process_frame(self) -> StepResult:
        frame = self._dfs_stack[-1]
        if frame.next_index >= len(frame.neighbors):
            self._dfs_stack.pop()
            if self._path_edges:
                self._path_edges.pop()
            if not self._dfs_stack:
                return self._make_result(
                    frame.left,
                    None,
                    f"No augmenting path from {frame.left}",
                )
            return self._make_result(frame.left, None, "Backtrack")

        neighbor = frame.neighbors[frame.next_index]
        frame.next_index += 1
        edge = (frame.left, neighbor)
        if neighbor in self._visited_right:
            return self._make_result(
                frame.left,
                edge,
                f"Skipping {neighbor}, already visited",
            )
        self._visited_right.add(neighbor)

        if neighbor not in self._matches:
            self._path_edges.append(edge)
            for left_node, right_node in self._path_edges:
                self._matches[right_node] = left_node
                self._left_matched[left_node] = right_node
            self._path_edges.clear()
            self._dfs_stack.clear()
            self._visited_right.clear()
            return self._make_result(
                frame.left,
                edge,
                "Augmenting path found, matching grows",
            )

        matched_left = self._matches[neighbor]
        self._path_edges.append(edge)
        self._dfs_stack.append(
            _Frame(matched_left, list(self._adjacency[matched_left]))
        )
        return self._make_result(
            frame.left,
            edge,
            f"Following matched edge through {neighbor} to {matched_left}",
        )

    def _make_result(
        self,
        current: int | None,
        current_edge: tuple[int, int] | None,
        message: str,
    ) -> StepResult:
        node_colors: dict[int, str] = {}
        for left_node in self._left_matched:
            node_colors[left_node] = MATCHED_COLOR
        for right_node in self._matches:
            node_colors[right_node] = MATCHED_COLOR
        for frame in self._dfs_stack:
            node_colors[frame.left] = ON_PATH_COLOR
        for _, right_node in self._path_edges:
            node_colors[right_node] = ON_PATH_COLOR

        return StepResult(
            current=current,
            current_edge=current_edge,
            tree_edges=frozenset(self._left_matched.items()),
            node_colors=node_colors,
            info=message,
        )


def _partition(graph: Graph) -> tuple[set[int], set[int]]:
    """Split a bipartite graph into two color classes.

    Args:
        graph: The graph to partition.

    Returns:
        A tuple of two sets of node ids, one per color class.

    Raises:
        ValueError: If the graph is not bipartite.
    """
    adjacency: dict[int, list[int]] = {node.id: [] for node in graph.nodes()}
    for edge in graph.edges():
        if edge.source == edge.target:
            continue
        adjacency[edge.source].append(edge.target)
        adjacency[edge.target].append(edge.source)

    color: dict[int, int] = {}
    for start in adjacency:
        if start in color:
            continue
        color[start] = 0
        queue: deque[int] = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if neighbor not in color:
                    color[neighbor] = 1 - color[node]
                    queue.append(neighbor)
                elif color[neighbor] == color[node]:
                    raise ValueError("Graph is not bipartite")

    left = {node for node, component in color.items() if component == 0}
    right = {node for node, component in color.items() if component == 1}
    return left, right
