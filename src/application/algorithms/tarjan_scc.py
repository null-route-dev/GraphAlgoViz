"""Tarjan's strongly connected components algorithm."""

from dataclasses import dataclass

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

SCC_PALETTE: tuple[str, ...] = (
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#b07aa1",
    "#76b7b2",
    "#edc948",
    "#9c755f",
    "#bab0ac",
)


@dataclass
class _Frame:
    """One active DFS frame in the iterative Tarjan algorithm.

    Args:
        node: Id of the node this frame belongs to.
        neighbors: Outgoing neighbors of the node, materialized once.
        next_neighbor: Index of the next neighbor to process.
    """

    node: int
    neighbors: list[int]
    next_neighbor: int = 0


class TarjanSCC(BaseAlgorithm):
    """Tarjan's strongly connected components algorithm.

    The algorithm performs a depth-first search on the directed graph
    and identifies strongly connected components using low-link
    values. A node is the root of an SCC when its low-link value
    equals its discovery index. When that happens, every node on the
    algorithm's internal stack up to and including the root belongs
    to the same SCC.

    The algorithm is iterative: each visible step corresponds to one
    concrete action — entering a node, processing one outgoing edge,
    or finishing a node (which either closes an SCC or propagates a
    low-link value up the DFS tree). This granularity makes every
    state transition observable.

    Tarjan processes the whole graph, not just nodes reachable from
    the start node. The start node is accepted for interface
    compatibility with the algorithm registry and is only validated;
    it does not affect the result.

    Undirected graphs are treated as bidirectional directed graphs.
    Every connected component then becomes a single SCC.

    Args:
        graph: The graph to process.
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
        self._neighbors_of: dict[int, list[int]] = {
            node.id: graph.neighbors(node.id) for node in graph.nodes()
        }

        self._indices: dict[int, int] = {}
        self._lowlink: dict[int, int] = {}
        self._tarjan_stack: list[int] = []
        self._on_stack: set[int] = set()
        self._sccs: list[list[int]] = []
        self._scc_of: dict[int, int] = {}
        self._tree_edges: set[tuple[int, int]] = set()

        self._dfs_stack: list[_Frame] = []
        self._next_root_pos = 0
        self._index_counter = 0
        self._finished = False

    @property
    def is_finished(self) -> bool:
        """Whether the algorithm has processed the whole graph.

        Returns:
            True if every SCC has been found.
        """
        return self._finished

    @property
    def scc_count(self) -> int:
        """Number of SCCs found so far.

        Returns:
            The number of completed SCCs.
        """
        return len(self._sccs)

    def scc_of(self, node_id: int) -> int | None:
        """Return the index of the SCC containing the given node.

        Args:
            node_id: Identifier of the node.

        Returns:
            The SCC index, or None if the node is not yet in a
            completed SCC.
        """
        return self._scc_of.get(node_id)

    def sccs(self) -> list[list[int]]:
        """Return the SCCs found so far, sorted for stable comparison.

        Each inner list contains the node ids of one SCC, sorted
        ascending. The outer list is sorted by the smallest node id
        of each SCC.

        Returns:
            A list of SCC node id lists.
        """
        return sorted(
            (sorted(scc) for scc in self._sccs),
            key=lambda scc: scc[0] if scc else 0,
        )

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
        if frame.next_neighbor < len(frame.neighbors):
            neighbor = frame.neighbors[frame.next_neighbor]
            frame.next_neighbor += 1
            return self._process_edge(frame.node, neighbor)
        self._dfs_stack.pop()
        return self._finish_node(frame.node)

    def _handle_no_active_frame(self) -> StepResult:
        while self._next_root_pos < len(self._node_order):
            root = self._node_order[self._next_root_pos]
            self._next_root_pos += 1
            if root not in self._indices:
                self._enter_node(root)
                return self._make_result(root, f"Entered root {root}")
        self._finished = True
        return self._make_result(
            None,
            f"Finished: {len(self._sccs)} SCC(s) found",
        )

    def _enter_node(self, node_id: int) -> None:
        self._indices[node_id] = self._index_counter
        self._lowlink[node_id] = self._index_counter
        self._index_counter += 1
        self._tarjan_stack.append(node_id)
        self._on_stack.add(node_id)
        self._dfs_stack.append(
            _Frame(
                node=node_id,
                neighbors=list(self._neighbors_of[node_id]),
            )
        )

    def _process_edge(self, from_node: int, to_node: int) -> StepResult:
        if to_node not in self._indices:
            self._tree_edges.add((from_node, to_node))
            self._enter_node(to_node)
            return self._make_result(
                from_node,
                f"Edge {from_node} \u2192 {to_node}: discovered {to_node}",
            )

        if to_node in self._on_stack:
            old = self._lowlink[from_node]
            self._lowlink[from_node] = min(old, self._indices[to_node])
            if self._lowlink[from_node] != old:
                return self._make_result(
                    from_node,
                    f"Edge {from_node} \u2192 {to_node}: "
                    f"lowlink[{from_node}] = {self._lowlink[from_node]}",
                )
            return self._make_result(
                from_node,
                f"Edge {from_node} \u2192 {to_node}: no update",
            )

        return self._make_result(
            from_node,
            f"Edge {from_node} \u2192 {to_node}: target in completed SCC",
        )

    def _finish_node(self, node_id: int) -> StepResult:
        if self._lowlink[node_id] == self._indices[node_id]:
            scc = self._pop_scc(node_id)
            scc_id = len(self._sccs)
            self._sccs.append(scc)
            for nid in scc:
                self._scc_of[nid] = scc_id
            return self._make_result(
                node_id,
                f"Closed SCC {sorted(scc)}",
            )

        if self._dfs_stack:
            parent = self._dfs_stack[-1].node
            self._lowlink[parent] = min(self._lowlink[parent], self._lowlink[node_id])
        return self._make_result(
            node_id,
            f"Finished {node_id}: lowlink = {self._lowlink[node_id]}",
        )

    def _pop_scc(self, root: int) -> list[int]:
        scc: list[int] = []
        while True:
            top = self._tarjan_stack.pop()
            self._on_stack.discard(top)
            scc.append(top)
            if top == root:
                break
        scc.reverse()
        return scc

    def _make_result(self, current: int | None, message: str) -> StepResult:
        colors: dict[int, str] = {}
        for scc_id, scc in enumerate(self._sccs):
            color = SCC_PALETTE[scc_id % len(SCC_PALETTE)]
            for nid in scc:
                colors[nid] = color
        return StepResult(
            visited=frozenset(self._indices.keys()),
            current=current,
            frontier=tuple(self._tarjan_stack),
            tree_edges=frozenset(self._tree_edges),
            node_colors=colors,
            info=message,
        )
