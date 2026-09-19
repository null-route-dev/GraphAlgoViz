"""Tests for the Node entity."""

from domain.entities.node import Node


def test_create_node_with_id_only() -> None:
    """Node can be created with only an id."""
    node = Node(id=1)
    assert node.id == 1
    assert node.label == ""


def test_create_node_with_label() -> None:
    """Node stores the provided label."""
    node = Node(id=1, label="A")
    assert node.id == 1
    assert node.label == "A"


def test_nodes_with_same_data_are_equal() -> None:
    """Two nodes with the same id and label compare as equal."""
    assert Node(id=1, label="A") == Node(id=1, label="A")


def test_nodes_with_different_ids_are_not_equal() -> None:
    """Nodes with different ids compare as not equal."""
    assert Node(id=1) != Node(id=2)
