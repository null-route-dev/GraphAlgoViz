"""Bridges and articulation points via iterative DFS."""

from dataclasses import dataclass

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

ARTICULATION_COLOR = "#9467bd"


@dataclass
class _Frame:
    """One active DFS frame.

    Args:
        node: Id of the node this frame belongs to.
        adjacency: Materialized list of (neighbor, edge_index) pairs.
        next_index: Index of the next adjacency entry to process.
    """

    node: int
    adjacency: list[tuple[int, int]]
    next_index: int = 0


class BridgesAndArticulations(BaseAlgorithm):
    """Bridges and articulation points of an undirected graph.

    A bridge is an edge whose removal disconnects its connected
    component. An articulation point is a node whose removal increases
    the number of connected components. Both are found in a single
    DFS pass using discovery times and low-link values.

    The algorithm is iterative: every visible step is one concrete
    action — entering a node, processing one outgoing edge, or
    finishing a node and applying the bridge / articulation rules
    at that moment. A single finish step can report both a bridge
    and an articulation point; the info string combines them.

    The graph is treated as undirected. Directed edges are traversed
    in both directions, as if the graph were undirected. The result
    describes the underlying undirected graph, which is the only
    setting in which bridges and articulation points are defined.

    Parallel edges between the same pair of nodes are handled
    correctly: a pair connected by two or more edges never forms a
    bridge, because the second edge provides an alternative route.
    This is achieved by tracking edge indices rather than node ids
    when deciding whether an edge is the one to the parent.

    The start node is accepted for interface compatibility with the
    algorithm registry. The whole graph is processed regardless of
    which node is chosen, so the value is only validated.

    Args:
        graph: The graph to analyse.
        start_node_id: Id of an existing node, used only for
            validation.

    Raises:
        ValueError: If the start node does not exist in the graph.
    """

    def __init__(self, graph: Graph, start_node_id: int) -> None:
        if not graph.has_node(start_node_id):
            raise ValueError(f"Start node {start_node_id} does not exist")

        self._graph = graph
        self._node_order: list[int] = [node.id for node in graph.nodes()]

        adjacency: dict[int, list[tuple[int, int]]] = {
            node.id: [] for node in graph.nodes()
        }
        for index, edge in enumerate(graph.edges()):
            adjacency[edge.source].append((edge.target, index))
            adjacency[edge.target].append((edge.source, index))
        self._adjacency = adjacency

        self._disc: dict[int, int] = {}
        self._low: dict[int, int] = {}
        self._parent: dict[int, int | None] = {}
        self._parent_edge: dict[int, int | None] = {}
        self._children: dict[int, int] = {}
        self._bridges: set[tuple[int, int]] = set()
        self._articulations: set[int] = set()

        self._dfs_stack: list[_Frame] = []
        self._time = 0
        self._next_root_pos = 0
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether the whole graph has been processed.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    @property
    def bridges(self) -> list[tuple[int, int]]:
        """Bridges found so far, sorted.

        Returns:
            A list of (min_id, max_id) pairs.
        """
        return sorted(self._bridges)

    @property
    def articulation_points(self) -> list[int]:
        """Articulation points found so far, sorted.

        Returns:
            A list of node ids.
        """
        return sorted(self._articulations)

    def lowlink_of(self, node_id: int) -> int | None:
        """Return the low-link value of a node.

        Args:
            node_id: Identifier of the node.

        Returns:
            The low-link value, or None if the node is not visited.
        """
        return self._low.get(node_id)

    def step(self) -> StepResult:
        """Perform one step of the algorithm.

        Returns:
            A snapshot of the current state.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        if not self._dfs_stack:
            return self._handle_no_active_frame()

        frame = self._dfs_stack[-1]
        if frame.next_index < len(frame.adjacency):
            neighbor, edge_index = frame.adjacency[frame.next_index]
            frame.next_index += 1
            return self._process_edge(frame.node, neighbor, edge_index)

        self._dfs_stack.pop()
        return self._finish_node(frame.node)

    def _handle_no_active_frame(self) -> StepResult:
        while self._next_root_pos < len(self._node_order):
            root = self._node_order[self._next_root_pos]
            self._next_root_pos += 1
            if root not in self._disc:
                self._enter_root(root)
                return self._make_result(root, f"Entered root {root}")
        self._finished = True
        return self._make_result(
            None,
            f"Finished: {len(self._bridges)} bridge(s), "
            f"{len(self._articulations)} articulation point(s)",
        )

    def _enter_root(self, node_id: int) -> None:
        self._disc[node_id] = self._time
        self._low[node_id] = self._time
        self._time += 1
        self._parent[node_id] = None
        self._parent_edge[node_id] = None
        self._children[node_id] = 0
        self._dfs_stack.append(
            _Frame(
                node=node_id,
                adjacency=list(self._adjacency[node_id]),
            )
        )

    def _enter_child(self, node_id: int, parent: int, edge_index: int) -> None:
        self._disc[node_id] = self._time
        self._low[node_id] = self._time
        self._time += 1
        self._parent[node_id] = parent
        self._parent_edge[node_id] = edge_index
        self._children[node_id] = 0
        self._dfs_stack.append(
            _Frame(
                node=node_id,
                adjacency=list(self._adjacency[node_id]),
            )
        )

    def _process_edge(
        self,
        from_node: int,
        to_node: int,
        edge_index: int,
    ) -> StepResult:
        if to_node not in self._disc:
            self._children[from_node] += 1
            self._enter_child(to_node, from_node, edge_index)
            return self._make_result(
                from_node,
                f"Tree edge {from_node}-{to_node}",
            )

        if edge_index == self._parent_edge[from_node]:
            return self._make_result(
                from_node,
                f"Skip parent edge {from_node}-{to_node}",
            )

        old = self._low[from_node]
        self._low[from_node] = min(old, self._disc[to_node])
        if self._low[from_node] != old:
            return self._make_result(
                from_node,
                f"Back edge {from_node}-{to_node}: "
                f"lowlink[{from_node}] = {self._low[from_node]}",
            )
        return self._make_result(
            from_node,
            f"Back edge {from_node}-{to_node}: no change",
        )

    def _finish_node(self, node_id: int) -> StepResult:
        parent = self._parent[node_id]
        events: list[str] = []

        if parent is not None:
            self._low[parent] = min(self._low[parent], self._low[node_id])

            if self._low[node_id] > self._disc[parent]:
                a, b = sorted((parent, node_id))
                if (a, b) not in self._bridges:
                    self._bridges.add((a, b))
                    events.append(f"Bridge found: {parent}-{node_id}")

            if (
                self._low[node_id] >= self._disc[parent]
                and self._parent[parent] is not None
                and parent not in self._articulations
            ):
                self._articulations.add(parent)
                events.append(f"Articulation point: {parent}")

        if (
            parent is None
            and self._children[node_id] > 1
            and node_id not in self._articulations
        ):
            self._articulations.add(node_id)
            events.append(f"Root articulation point: {node_id}")

        if not events:
            events.append(f"Finished {node_id}: lowlink = {self._low[node_id]}")

        return self._make_result(node_id, "; ".join(events))

    def _make_result(self, current: int | None, message: str) -> StepResult:
        colors: dict[int, str] = {
            nid: ARTICULATION_COLOR for nid in self._articulations
        }
        labels = {nid: str(low) for nid, low in self._low.items()}
        frontier = tuple(frame.node for frame in self._dfs_stack)
        return StepResult(
            visited=frozenset(self._disc.keys()),
            current=current,
            frontier=frontier,
            tree_edges=frozenset(self._bridges),
            labels=labels,
            node_colors=colors,
            info=message,
        )
