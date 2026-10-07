"""Kruskal's minimum spanning tree algorithm with step-by-step output."""

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from domain.entities.graph import Graph

COMPONENT_PALETTE: tuple[str, ...] = (
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#b07aa1",
    "#76b7b2",
    "#edc948",
    "#9c755f",
    "#bab0ac",
)


class _UnionFind:
    """Disjoint-set forest with path compression and union by rank.

    Args:
        elements: The initial set of elements. Each starts in its own
            component.
    """

    def __init__(self, elements: list[int]) -> None:
        self._parent: dict[int, int] = {e: e for e in elements}
        self._rank: dict[int, int] = {e: 0 for e in elements}

    def find(self, x: int) -> int:
        """Return the representative of the component containing x.

        Args:
            x: The element to look up.

        Returns:
            The root of x's component.
        """
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int) -> bool:
        """Merge the components containing x and y.

        Args:
            x: An element in the first component.
            y: An element in the second component.

        Returns:
            True if the components were merged, False if x and y were
            already in the same component.
        """
        rx = self.find(x)
        ry = self.find(y)
        if rx == ry:
            return False
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
        return True


class KruskalMST(BaseAlgorithm):
    """Kruskal's minimum spanning tree algorithm.

    The algorithm sorts all edges by weight and processes them one by
    one. An edge is added to the tree if its endpoints belong to
    different components, using a Union-Find structure. Otherwise the
    edge is rejected because adding it would create a cycle.

    The result is the minimum spanning forest of the graph: one tree
    per connected component. For a connected graph, this is the
    minimum spanning tree.

    Kruskal works on undirected graphs. Directed edges are treated as
    undirected for the purposes of the MST, since the concept of a
    spanning tree assumes undirected connectivity. This is documented
    rather than enforced, to keep the algorithm usable on mixed graphs.

    The starting node id is accepted for interface compatibility with
    the algorithm registry. The algorithm processes edges globally,
    not from a start node, so the value is only used to validate that
    the graph contains the node. It does not affect the result.

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
        self._node_ids: list[int] = [node.id for node in graph.nodes()]
        self._edges: list[tuple[int, int, float]] = [
            (edge.source, edge.target, edge.weight) for edge in graph.edges()
        ]
        self._edges.sort(key=lambda item: item[2])
        self._index = 0
        self._union_find = _UnionFind(self._node_ids)
        self._tree_edges: set[tuple[int, int]] = set()
        self._total_weight = 0.0
        self._finished = not self._edges

    @property
    def is_finished(self) -> bool:
        """Whether every edge has been considered.

        Returns:
            True if no further steps can be taken.
        """
        return self._finished

    @property
    def total_weight(self) -> float:
        """Total weight of the edges in the spanning forest.

        Returns:
            The sum of weights of the accepted edges.
        """
        return self._total_weight

    def step(self) -> StepResult:
        """Consider the next edge in weight order.

        Returns:
            A snapshot showing the accepted edges, the edge under
            consideration, the current component coloring, and a
            description of the step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        if self._finished:
            raise RuntimeError("Algorithm already finished")

        source, target, weight = self._edges[self._index]
        accepted = self._union_find.union(source, target)

        if accepted:
            self._tree_edges.add((source, target))
            self._total_weight += weight
            message = (
                f"Accepted edge {source}-{target} "
                f"(weight {weight:g}), total {self._total_weight:g}"
            )
        else:
            message = (
                f"Rejected edge {source}-{target} "
                f"(weight {weight:g}) — would create a cycle"
            )

        self._index += 1
        if self._index >= len(self._edges):
            self._finished = True

        return StepResult(
            visited=frozenset(self._node_ids),
            current=source,
            current_edge=(source, target),
            tree_edges=frozenset(self._tree_edges),
            node_colors=self._component_colors(),
            info=message,
        )

    def _component_colors(self) -> dict[int, str]:
        roots = sorted({self._union_find.find(nid) for nid in self._node_ids})
        color_by_root = {
            root: COMPONENT_PALETTE[i % len(COMPONENT_PALETTE)]
            for i, root in enumerate(roots)
        }
        return {
            nid: color_by_root[self._union_find.find(nid)] for nid in self._node_ids
        }
