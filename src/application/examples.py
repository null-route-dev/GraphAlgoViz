"""Pre-built example graphs with hand-picked node positions."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node
from domain.value_objects.position import Position

BuilderResult = tuple[Graph, dict[int, Position]]


@dataclass(frozen=True)
class GraphExample:
    """A named example graph with pre-set node positions.

    Args:
        id: Stable identifier used for programmatic lookup.
        display_name: Human-readable name shown in the menu.
        description: Short explanation shown as a tooltip.
        build: Callable returning a fresh graph and positions.
    """

    id: str
    display_name: str
    description: str
    build: Callable[[], BuilderResult]


def _regular_polygon(
    n: int,
    radius: float = 0.35,
    start_angle: float = math.pi / 2,
) -> list[Position]:
    return [
        Position(
            x=0.5 + radius * math.cos(start_angle + i * 2 * math.pi / n),
            y=0.5 + radius * math.sin(start_angle + i * 2 * math.pi / n),
        )
        for i in range(n)
    ]


def build_k5() -> BuilderResult:
    """Return K5, the complete graph on five vertices.

    Returns:
        A graph with nodes 1..5 and all ten edges, laid out as a
        regular pentagon.
    """
    graph = Graph()
    for i in range(1, 6):
        graph.add_node(Node(id=i))
    for u in range(1, 6):
        for v in range(u + 1, 6):
            graph.add_edge(Edge(source=u, target=v))
    positions = {i + 1: pos for i, pos in enumerate(_regular_polygon(5))}
    return graph, positions


def build_k33() -> BuilderResult:
    """Return K3,3, the complete bipartite graph on 3+3 vertices.

    Returns:
        A graph with left nodes 1..3, right nodes 4..6, and all nine
        edges between them. Left column on the left, right column on
        the right.
    """
    graph = Graph()
    for i in range(1, 7):
        graph.add_node(Node(id=i))
    for u in (1, 2, 3):
        for v in (4, 5, 6):
            graph.add_edge(Edge(source=u, target=v))
    positions = {
        1: Position(x=0.3, y=0.75),
        2: Position(x=0.3, y=0.5),
        3: Position(x=0.3, y=0.25),
        4: Position(x=0.7, y=0.75),
        5: Position(x=0.7, y=0.5),
        6: Position(x=0.7, y=0.25),
    }
    return graph, positions


def build_binary_tree() -> BuilderResult:
    """Return a perfect binary tree of depth two (seven nodes).

    Returns:
        A graph with root at the top, two children, and four leaves,
        laid out in the classic triangular tree shape.
    """
    graph = Graph()
    for i in range(1, 8):
        graph.add_node(Node(id=i))
    for u, v in ((1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)):
        graph.add_edge(Edge(source=u, target=v))
    positions = {
        1: Position(x=0.5, y=0.85),
        2: Position(x=0.3, y=0.6),
        3: Position(x=0.7, y=0.6),
        4: Position(x=0.15, y=0.35),
        5: Position(x=0.4, y=0.35),
        6: Position(x=0.6, y=0.35),
        7: Position(x=0.85, y=0.35),
    }
    return graph, positions


def build_cycle() -> BuilderResult:
    """Return C6, the cycle graph on six vertices.

    Returns:
        A graph with nodes 1..6 and a cycle of six edges, laid out as
        a regular hexagon.
    """
    graph = Graph()
    n = 6
    for i in range(1, n + 1):
        graph.add_node(Node(id=i))
    for i in range(1, n):
        graph.add_edge(Edge(source=i, target=i + 1))
    graph.add_edge(Edge(source=n, target=1))
    positions = {i + 1: pos for i, pos in enumerate(_regular_polygon(n))}
    return graph, positions


def build_petersen() -> BuilderResult:
    """Return the Petersen graph with the classic layout.

    Returns:
        A graph with ten nodes and fifteen edges. The outer pentagon
        (nodes 1..5) surrounds the inner pentagram (nodes 6..10), with
        radial rungs connecting corresponding pairs.
    """
    graph = Graph()
    for i in range(1, 11):
        graph.add_node(Node(id=i))
    outer = ((1, 2), (2, 3), (3, 4), (4, 5), (5, 1))
    inner = ((6, 8), (8, 10), (10, 7), (7, 9), (9, 6))
    rungs = ((1, 6), (2, 7), (3, 8), (4, 9), (5, 10))
    for u, v in outer + inner + rungs:
        graph.add_edge(Edge(source=u, target=v))
    outer_r = 0.4
    inner_r = 0.18
    positions: dict[int, Position] = {}
    for i in range(5):
        angle = math.pi / 2 + i * 2 * math.pi / 5
        positions[i + 1] = Position(
            x=0.5 + outer_r * math.cos(angle),
            y=0.5 + outer_r * math.sin(angle),
        )
        angle_inner = angle + math.pi / 5
        positions[i + 6] = Position(
            x=0.5 + inner_r * math.cos(angle_inner),
            y=0.5 + inner_r * math.sin(angle_inner),
        )
    return graph, positions


_DODECAHEDRON_EDGES: tuple[tuple[int, int], ...] = (
    (1, 2),
    (1, 11),
    (1, 20),
    (2, 3),
    (2, 9),
    (3, 4),
    (3, 7),
    (4, 5),
    (4, 20),
    (5, 6),
    (5, 18),
    (6, 7),
    (6, 16),
    (7, 8),
    (8, 9),
    (8, 15),
    (9, 10),
    (10, 11),
    (10, 14),
    (11, 12),
    (12, 13),
    (12, 19),
    (13, 14),
    (13, 17),
    (14, 15),
    (15, 16),
    (16, 17),
    (17, 18),
    (18, 19),
    (19, 20),
)


def build_dodecahedron() -> BuilderResult:
    """Return the dodecahedral graph on twenty vertices.

    Returns:
        A graph with twenty nodes, thirty edges, every vertex of
        degree three, laid out as a regular 20-gon.
    """
    graph = Graph()
    for i in range(1, 21):
        graph.add_node(Node(id=i))
    for u, v in _DODECAHEDRON_EDGES:
        graph.add_edge(Edge(source=u, target=v))
    positions = {i + 1: pos for i, pos in enumerate(_regular_polygon(20, radius=0.4))}
    return graph, positions


def all_examples() -> list[GraphExample]:
    """Return every available example in display order.

    Returns:
        A list of GraphExample objects.
    """
    return [
        GraphExample(
            id="k5",
            display_name="K5 (complete graph)",
            description="Complete graph on five vertices.",
            build=build_k5,
        ),
        GraphExample(
            id="k33",
            display_name="K3,3 (complete bipartite)",
            description=(
                "Complete bipartite graph with three left and three right nodes."
            ),
            build=build_k33,
        ),
        GraphExample(
            id="tree",
            display_name="Binary tree (depth 2)",
            description=(
                "Perfect binary tree with a root, two children, and four leaves."
            ),
            build=build_binary_tree,
        ),
        GraphExample(
            id="cycle",
            display_name="Cycle C6",
            description="Cycle of six nodes.",
            build=build_cycle,
        ),
        GraphExample(
            id="petersen",
            display_name="Petersen graph",
            description=(
                "Classic Petersen graph with ten nodes and fifteen "
                "edges, all of degree three."
            ),
            build=build_petersen,
        ),
        GraphExample(
            id="dodecahedron",
            display_name="Dodecahedron",
            description=(
                "Dodecahedral graph with twenty nodes and thirty "
                "edges, all of degree three."
            ),
            build=build_dodecahedron,
        ),
    ]


def find_example(example_id: str) -> GraphExample:
    """Return the example with the given id.

    Args:
        example_id: Stable identifier of the example.

    Returns:
        The matching GraphExample.

    Raises:
        KeyError: If no example with the given id exists.
    """
    for example in all_examples():
        if example.id == example_id:
            return example
    raise KeyError(f"Unknown example '{example_id}'")
