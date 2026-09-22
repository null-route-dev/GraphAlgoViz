"""Registry of graph algorithms available to the application."""

from collections.abc import Callable
from dataclasses import dataclass

from application.algorithms.base import BaseAlgorithm
from application.algorithms.breadth_first_search import BreadthFirstSearch
from application.algorithms.depth_first_search import DepthFirstSearch
from application.algorithms.dijkstra import Dijkstra
from domain.entities.graph import Graph

AlgorithmFactory = Callable[[Graph, int], BaseAlgorithm]


@dataclass(frozen=True)
class AlgorithmInfo:
    """Metadata describing a graph algorithm available to the application.

    Args:
        id: Unique stable identifier used for programmatic lookup.
        display_name: Human-readable name shown in the UI.
        description: Short explanation of what the algorithm does.
        factory: Callable that creates an algorithm instance from a
            graph and a start node id.
    """

    id: str
    display_name: str
    description: str
    factory: AlgorithmFactory


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
    ) -> BaseAlgorithm:
        """Instantiate an algorithm by id.

        Args:
            algorithm_id: Identifier of the algorithm.
            graph: The graph to run the algorithm on.
            start_node_id: Id of the start node.

        Returns:
            A fresh algorithm instance.

        Raises:
            KeyError: If no algorithm with the given id is registered.
        """
        return self.get(algorithm_id).factory(graph, start_node_id)

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
        A new registry containing depth-first search, breadth-first
        search, and Dijkstra.
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
            factory=DepthFirstSearch,
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
            factory=BreadthFirstSearch,
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
            factory=Dijkstra,
        )
    )
    return registry
