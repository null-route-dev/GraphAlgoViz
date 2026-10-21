"""Tests for the CSV graph exporter."""

from pathlib import Path

import pytest

from application.csv_export import CSV_HEADER, export_csv
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node


def _read_rows(path: Path) -> list[list[str]]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def test_header_is_written(tmp_path: Path) -> None:
    """The first row is the expected header."""
    path = tmp_path / "out.csv"
    export_csv(Graph(), path)

    rows = _read_rows(path)
    assert rows[0] == list(CSV_HEADER)


def test_empty_graph_writes_header_only(tmp_path: Path) -> None:
    """An empty graph produces a file with only the header."""
    path = tmp_path / "out.csv"
    export_csv(Graph(), path)

    assert len(_read_rows(path)) == 1


def test_undirected_edge_is_written(tmp_path: Path) -> None:
    """An undirected edge is written with directed=false."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=1.5))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    rows = _read_rows(path)
    assert rows[1] == ["1", "2", "1.5", "false"]


def test_directed_edge_is_written(tmp_path: Path) -> None:
    """A directed edge is written with directed=true."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=2.0, directed=True))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    rows = _read_rows(path)
    assert rows[1] == ["1", "2", "2", "true"]


def test_integer_weight_has_no_decimal_point(tmp_path: Path) -> None:
    """Weights are written without trailing zeros."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=3.0))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    assert _read_rows(path)[1][2] == "3"


def test_isolated_node_is_written(tmp_path: Path) -> None:
    """An isolated node appears as a row with empty target."""
    graph = Graph()
    graph.add_node(Node(id=7))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    rows = _read_rows(path)
    assert rows[1] == ["7", "", "", ""]


def test_non_isolated_node_is_not_duplicated(tmp_path: Path) -> None:
    """A node with an incident edge appears only in the edge row."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    rows = _read_rows(path)
    assert len(rows) == 2
    assert rows[1][0] == "1"
    assert rows[1][1] == "2"


def test_isolated_nodes_sorted_before_edges(tmp_path: Path) -> None:
    """Isolated nodes are emitted before edges, in id order."""
    graph = Graph()
    for i in (1, 2, 3, 4):
        graph.add_node(Node(id=i))
    graph.add_edge(Edge(source=2, target=3))
    path = tmp_path / "out.csv"

    export_csv(graph, path)

    rows = _read_rows(path)
    isolated = [row for row in rows[1:] if row[1] == ""]
    assert [row[0] for row in isolated] == ["1", "4"]


def test_round_trip_preserves_graph(tmp_path: Path) -> None:
    """Export followed by import reproduces the original graph."""
    from application.csv_import import import_csv

    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_node(Node(id=3))
    graph.add_node(Node(id=9))
    graph.add_edge(Edge(source=1, target=2, weight=1.5))
    graph.add_edge(Edge(source=2, target=3, weight=2.0, directed=True))
    path = tmp_path / "out.csv"

    export_csv(graph, path)
    restored = import_csv(path)

    assert restored.node_count == 4
    assert restored.edge_count == 2
    assert restored.has_node(9) is True


def test_save_fails_on_missing_directory(tmp_path: Path) -> None:
    """A non-existent directory raises OSError."""
    path = tmp_path / "missing" / "out.csv"

    with pytest.raises(OSError):
        export_csv(Graph(), path)
