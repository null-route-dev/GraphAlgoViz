"""Tests for the JSON project storage."""

from pathlib import Path

import pytest

from application.project_storage import ProjectStorageError
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node
from domain.value_objects.position import Position
from infrastructure.serialization.json_project_storage import (
    JsonProjectStorage,
)


@pytest.fixture
def storage() -> JsonProjectStorage:
    """Return a JSON project storage."""
    return JsonProjectStorage()


def build_graph() -> Graph:
    """Return a graph with three nodes and two edges."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A"))
    graph.add_node(Node(id=2, label="B"))
    graph.add_node(Node(id=3))
    graph.add_edge(Edge(source=1, target=2, weight=1.5))
    graph.add_edge(Edge(source=2, target=3, weight=2.0, directed=True))
    return graph


def build_positions() -> dict[int, Position]:
    """Return positions for the three nodes of build_graph."""
    return {
        1: Position(x=0.1, y=0.2),
        2: Position(x=0.5, y=0.5),
        3: Position(x=0.9, y=0.8),
    }


def test_save_creates_file(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """save writes a file at the given path."""
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), build_positions(), path)

    assert path.exists()
    assert path.stat().st_size > 0


def test_round_trip_preserves_node_count(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """The number of nodes is preserved across save and load."""
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), build_positions(), path)
    loaded, _ = storage.load(path)

    assert loaded.node_count == 3


def test_round_trip_preserves_edge_count(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """The number of edges is preserved across save and load."""
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), build_positions(), path)
    loaded, _ = storage.load(path)

    assert loaded.edge_count == 2


def test_round_trip_preserves_node_labels(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Node labels survive the round trip."""
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), build_positions(), path)
    loaded, _ = storage.load(path)

    assert loaded.node(1).label == "A"
    assert loaded.node(2).label == "B"
    assert loaded.node(3).label == ""


def test_round_trip_preserves_positions(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Node positions survive the round trip."""
    positions = build_positions()
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), positions, path)
    _, loaded_positions = storage.load(path)

    assert loaded_positions == positions


def test_round_trip_preserves_edge_attributes(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Edge weight and direction survive the round trip."""
    path = tmp_path / "project.gaviz"
    storage.save(build_graph(), build_positions(), path)
    loaded, _ = storage.load(path)

    first = loaded.edges()[0]
    assert first.source == 1
    assert first.target == 2
    assert first.weight == 1.5
    assert first.directed is False

    second = loaded.edges()[1]
    assert second.directed is True


def test_load_raises_for_missing_file(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Loading a nonexistent file raises ProjectStorageError."""
    with pytest.raises(ProjectStorageError):
        storage.load(tmp_path / "missing.gaviz")


def test_load_raises_for_invalid_json(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Loading a file with broken JSON raises ProjectStorageError."""
    path = tmp_path / "bad.gaviz"
    path.write_text("not json at all", encoding="utf-8")

    with pytest.raises(ProjectStorageError):
        storage.load(path)


def test_load_raises_for_unsupported_version(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Loading a file with an unknown version raises ProjectStorageError."""
    path = tmp_path / "v99.gaviz"
    path.write_text(
        '{"version": 99, "nodes": [], "edges": []}',
        encoding="utf-8",
    )

    with pytest.raises(ProjectStorageError, match="unsupported version"):
        storage.load(path)


def test_load_raises_for_non_object_top_level(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """A JSON array at the top level is rejected."""
    path = tmp_path / "array.gaviz"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ProjectStorageError, match="must be an object"):
        storage.load(path)


def test_load_raises_for_malformed_node(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """A node without a position raises ProjectStorageError."""
    path = tmp_path / "broken.gaviz"
    path.write_text(
        '{"version": 1, "nodes": [{"id": 1, "label": "A"}], "edges": []}',
        encoding="utf-8",
    )

    with pytest.raises(ProjectStorageError, match="malformed"):
        storage.load(path)


def test_save_uses_default_position_for_missing_nodes(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """Nodes without a position entry are saved at the center."""
    graph = Graph()
    graph.add_node(Node(id=1))
    path = tmp_path / "no_pos.gaviz"

    storage.save(graph, {}, path)
    _, positions = storage.load(path)

    assert positions == {1: Position(x=0.5, y=0.5)}


def test_empty_graph_round_trips(
    storage: JsonProjectStorage,
    tmp_path: Path,
) -> None:
    """An empty graph saves and loads without errors."""
    path = tmp_path / "empty.gaviz"
    storage.save(Graph(), {}, path)
    loaded, positions = storage.load(path)

    assert loaded.node_count == 0
    assert loaded.edge_count == 0
    assert positions == {}
