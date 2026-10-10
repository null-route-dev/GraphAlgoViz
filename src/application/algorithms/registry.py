"""Registry of graph algorithms available to the application."""

from collections.abc import Callable
from dataclasses import dataclass

from application.algorithms.astar import AStar
from application.algorithms.base import BaseAlgorithm
from application.algorithms.bellman_ford import BellmanFord
from application.algorithms.bipartite_check import BipartiteCheck
from application.algorithms.breadth_first_search import BreadthFirstSearch
from application.algorithms.bridges_articulations import BridgesAndArticulations
from application.algorithms.depth_first_search import DepthFirstSearch
from application.algorithms.dijkstra import Dijkstra
from application.algorithms.floyd_warshall import FloydWarshall
from application.algorithms.greedy_coloring import GreedyColoring
from application.algorithms.kruskal_mst import KruskalMST
from application.algorithms.max_flow import MaxFlow
from application.algorithms.prim_mst import PrimMST
from application.algorithms.tarjan_scc import TarjanSCC
from application.algorithms.topological_sort import TopologicalSort
from domain.entities.graph import Graph

AlgorithmFactory = Callable[[Graph, int, int | None], BaseAlgorithm]


def _no_target(
    factory: Callable[[Graph, int], BaseAlgorithm],
) -> AlgorithmFactory:
    """Adapt a two-argument factory to the three-argument signature.

    Args:
        factory: A factory that takes only a graph and a start node.

    Returns:
        A factory that accepts and ignores an optional target node.
    """

    def wrapper(
        graph: Graph,
        start_node_id: int,
        target_node_id: int | None,
    ) -> BaseAlgorithm:
        _ = target_node_id
        return factory(graph, start_node_id)

    return wrapper


def _target_required_factory(
    factory: Callable[[Graph, int, int], BaseAlgorithm],
    name: str,
) -> AlgorithmFactory:
    """Adapt a factory that requires a target into the three-argument form.

    Args:
        factory: A factory that takes a graph, a start node, and a
            required target node.
        name: Display name of the algorithm, used in the error message.

    Returns:
        A factory that validates and passes the target node.
    """

    def wrapper(
        graph: Graph,
        start_node_id: int,
        target_node_id: int | None,
    ) -> BaseAlgorithm:
        if target_node_id is None:
            raise ValueError(f"{name} requires a target node")
        return factory(graph, start_node_id, target_node_id)

    return wrapper


@dataclass(frozen=True)
class AlgorithmInfo:
    """Metadata describing a graph algorithm available to the application.

    Args:
        id: Unique stable identifier used for programmatic lookup.
        display_name: Human-readable name shown in the UI.
        description: Short explanation of what the algorithm does.
        factory: Callable that creates an algorithm instance.
        requires_target: Whether the algorithm needs a target node.
    """

    id: str
    display_name: str
    description: str
    factory: AlgorithmFactory
    requires_target: bool = False


class AlgorithmRegistry:
    """A collection of algorithm metadata indexed by id.

    Registration order is preserved and used by ``all`` so that the UI
    can present algorithms in a stable, predictable order.
    """

    def __init__(self) -> None:
        self._algorithms: dict[str, AlgorithmInfo] = {}

    def register(self, info: AlgorithmInfo) -> None:
        """Register an algorithm.

        Args:
            info: Metadata describing the algorithm.

        Raises:
            ValueError: If an algorithm with the same id is already
                registered.
        """
        if info.id in self._algorithms:
            raise ValueError(f"Algorithm '{info.id}' is already registered")
        self._algorithms[info.id] = info

    def get(self, algorithm_id: str) -> AlgorithmInfo:
        """Return metadata for the given algorithm id.

        Args:
            algorithm_id: Identifier of the algorithm.

        Returns:
            Metadata for the requested algorithm.

        Raises:
            KeyError: If no algorithm with the given id is registered.
        """
        if algorithm_id not in self._algorithms:
            raise KeyError(f"Algorithm '{algorithm_id}' is not registered")
        return self._algorithms[algorithm_id]

    def create(
        self,
        algorithm_id: str,
        graph: Graph,
        start_node_id: int,
        target_node_id: int | None = None,
    ) -> BaseAlgorithm:
        """Instantiate an algorithm by id.

        Args:
            algorithm_id: Identifier of the algorithm.
            graph: The graph to run the algorithm on.
            start_node_id: Id of the start node.
            target_node_id: Id of the target node, if the algorithm
                requires one.

        Returns:
            A fresh algorithm instance.

        Raises:
            KeyError: If no algorithm with the given id is registered.
            ValueError: If the algorithm requires a target and none
                was provided.
        """
        return self.get(algorithm_id).factory(graph, start_node_id, target_node_id)

    def all(self) -> list[AlgorithmInfo]:
        """Return metadata for every registered algorithm.

        Returns:
            A list in registration order.
        """
        return list(self._algorithms.values())

    @property
    def count(self) -> int:
        """Number of registered algorithms.

        Returns:
            The number of registered algorithms.
        """
        return len(self._algorithms)


def build_default_registry() -> AlgorithmRegistry:
    """Return a registry pre-populated with the built-in algorithms.

    Returns:
        A new registry containing all built-in algorithms.
    """
    registry = AlgorithmRegistry()
    registry.register(
        AlgorithmInfo(
            id="dfs",
            display_name="Depth-First Search",
            description=(
                "Traverses the graph by exploring as far as possible "
                "along each branch before backtracking."
            ),
            factory=_no_target(DepthFirstSearch),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="bfs",
            display_name="Breadth-First Search",
            description=(
                "Traverses the graph level by level, visiting all "
                "neighbours of a node before going deeper."
            ),
            factory=_no_target(BreadthFirstSearch),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="dijkstra",
            display_name="Dijkstra's Algorithm",
            description=(
                "Finds shortest paths from the start node using "
                "non-negative edge weights."
            ),
            factory=_no_target(Dijkstra),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="astar",
            display_name="A* Search",
            description=(
                "Finds the shortest path to a target node using a "
                "heuristic to guide the search."
            ),
            factory=_target_required_factory(AStar, "A*"),
            requires_target=True,
        )
    )
    registry.register(
        AlgorithmInfo(
            id="bellman-ford",
            display_name="Bellman-Ford",
            description=(
                "Finds shortest paths from the start node with "
                "arbitrary edge weights and detects negative cycles."
            ),
            factory=_no_target(BellmanFord),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="floyd-warshall",
            display_name="Floyd-Warshall",
            description=(
                "Computes shortest paths between every pair of nodes "
                "and shows the distances as a matrix."
            ),
            factory=_no_target(FloydWarshall),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="prim",
            display_name="Prim's Minimum Spanning Tree",
            description=(
                "Builds a minimum spanning tree by repeatedly adding "
                "the cheapest edge connecting a new node to the tree."
            ),
            factory=_no_target(PrimMST),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="kruskal",
            display_name="Kruskal's Minimum Spanning Tree",
            description=(
                "Builds a minimum spanning tree by processing edges "
                "in weight order and rejecting those that would form "
                "a cycle."
            ),
            factory=_no_target(KruskalMST),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="tarjan",
            display_name="Tarjan's Strongly Connected Components",
            description=(
                "Finds strongly connected components in a directed "
                "graph using a single depth-first traversal."
            ),
            factory=_no_target(TarjanSCC),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="bridges",
            display_name="Bridges and Articulation Points",
            description=(
                "Finds edges whose removal disconnects the graph and "
                "nodes whose removal does the same."
            ),
            factory=_no_target(BridgesAndArticulations),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="max-flow",
            display_name="Maximum Flow (Edmonds-Karp)",
            description=(
                "Computes the maximum flow from a source to a sink "
                "using the Edmonds-Karp algorithm."
            ),
            factory=_target_required_factory(MaxFlow, "Maximum flow"),
            requires_target=True,
        )
    )
    registry.register(
        AlgorithmInfo(
            id="bipartite",
            display_name="Bipartite Check",
            description=(
                "Checks whether the graph can be split into two "
                "independent sets by attempting a two-coloring."
            ),
            factory=_no_target(BipartiteCheck),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="coloring",
            display_name="Greedy Coloring",
            description=(
                "Colors nodes so that no two adjacent nodes share a "
                "color, picking the smallest available color for each."
            ),
            factory=_no_target(GreedyColoring),
        )
    )
    registry.register(
        AlgorithmInfo(
            id="toposort",
            display_name="Topological Sort",
            description=(
                "Orders nodes of a directed acyclic graph so that "
                "every directed edge goes from an earlier node to a "
                "later one."
            ),
            factory=_no_target(TopologicalSort),
        )
    )
    return registry
