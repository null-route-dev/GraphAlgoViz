"""Tests for the layout service."""

import math

import pytest

from application.services.layout_service import LayoutService
from domain.entities.graph import Graph
from domain.entities.node import Node
from domain.value_objects.position import Position


@pytest.fixture
def service() -> LayoutService:
    """Return a layout service."""
    return LayoutService()


def test_empty_graph_returns_empty_mapping(service: LayoutService) -> None:
    """An empty graph produces no positions."""
    assert service.circular(Graph()) == {}


def test_single_node_is_placed_at_center(service: LayoutService) -> None:
    """One node is placed at the center of the unit square."""
    graph = Graph()
    graph.add_node(Node(id=1))

    positions = service.circular(graph)

    assert positions == {1: Position(x=0.5, y=0.5)}


def test_two_nodes_are_opposite(service: LayoutService) -> None:
    """Two nodes are placed on opposite sides of the circle."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))

    positions = service.circular(graph)

    first = positions[1]
    second = positions[2]
    assert first.distance_to(second) == pytest.approx(0.8)


def test_every_node_receives_a_position(service: LayoutService) -> None:
    """Every node in the graph appears in the result."""
    graph = Graph()
    for node_id in range(1, 6):
        graph.add_node(Node(id=node_id))

    positions = service.circular(graph)

    assert set(positions.keys()) == {1, 2, 3, 4, 5}


def test_positions_lie_on_unit_circle(service: LayoutService) -> None:
    """Every position is at distance 0.4 from the center."""
    graph = Graph()
    for node_id in range(1, 4):
        graph.add_node(Node(id=node_id))

    positions = service.circular(graph)
    center = Position(x=0.5, y=0.5)

    for position in positions.values():
        assert position.distance_to(center) == pytest.approx(0.4)


def test_positions_are_evenly_spaced(service: LayoutService) -> None:
    """Nodes placed on a circle form equal angles."""
    graph = Graph()
    for node_id in range(1, 5):
        graph.add_node(Node(id=node_id))

    positions = service.circular(graph)

    angles = [math.atan2(pos.y - 0.5, pos.x - 0.5) for pos in positions.values()]
    angles.sort()
    gaps = [
        (angles[(i + 1) % len(angles)] - angles[i]) % (2 * math.pi)
        for i in range(len(angles))
    ]

    for gap in gaps:
        assert gap == pytest.approx(2 * math.pi / 4)
