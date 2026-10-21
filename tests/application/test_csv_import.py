"""Tests for the CSV graph importer."""

from pathlib import Path

import pytest

from application.csv_import import CsvFormatError, import_csv


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_empty_file_returns_empty_graph(tmp_path: Path) -> None:
    """A fully empty file produces an empty graph."""
    path = tmp_path / "in.csv"
    _write(path, "")

    assert import_csv(path).node_count == 0


def test_header_only_returns_empty_graph(tmp_path: Path) -> None:
    """A file with only a header produces an empty graph."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n")

    graph = import_csv(path)
    assert graph.node_count == 0
    assert graph.edge_count == 0


def test_single_edge(tmp_path: Path) -> None:
    """A single row produces a graph with two nodes and one edge."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n1,2,1.5,false\n")

    graph = import_csv(path)
    assert graph.node_count == 2
    assert graph.edge_count == 1
    edge = graph.edges()[0]
    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == pytest.approx(1.5)
    assert edge.directed is False


def test_default_weight_and_directed(tmp_path: Path) -> None:
    """Missing weight and directed columns default to 1.0 and False."""
    path = tmp_path / "in.csv"
    _write(path, "source,target\n1,2\n")

    graph = import_csv(path)
    edge = graph.edges()[0]
    assert edge.weight == pytest.approx(1.0)
    assert edge.directed is False


def test_directed_parsed_as_true(tmp_path: Path) -> None:
    """The string 'true' parses as a directed edge."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n1,2,2.0,true\n")

    graph = import_csv(path)
    assert graph.edges()[0].directed is True


def test_directed_accepts_yes(tmp_path: Path) -> None:
    """The string 'yes' also parses as directed."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n1,2,2.0,yes\n")

    graph = import_csv(path)
    assert graph.edges()[0].directed is True


def test_directed_accepts_one(tmp_path: Path) -> None:
    """The string '1' also parses as directed."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n1,2,2.0,1\n")

    graph = import_csv(path)
    assert graph.edges()[0].directed is True


def test_isolated_node_row(tmp_path: Path) -> None:
    """A row with empty target declares an isolated node."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight,directed\n5,,,\n")

    graph = import_csv(path)
    assert graph.node_count == 1
    assert graph.edge_count == 0
    assert graph.has_node(5) is True


def test_multiple_edges(tmp_path: Path) -> None:
    """Multiple data rows produce multiple edges."""
    path = tmp_path / "in.csv"
    _write(
        path,
        "source,target,weight,directed\n1,2,1.0,false\n2,3,2.0,true\n",
    )

    graph = import_csv(path)
    assert graph.node_count == 3
    assert graph.edge_count == 2


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    """Completely blank lines do not create edges."""
    path = tmp_path / "in.csv"
    _write(
        path,
        "source,target,weight,directed\n1,2,1.0,false\n\n",
    )

    graph = import_csv(path)
    assert graph.edge_count == 1


def test_header_case_insensitive(tmp_path: Path) -> None:
    """Header names are matched regardless of case."""
    path = tmp_path / "in.csv"
    _write(path, "SOURCE,TARGET\n1,2\n")

    graph = import_csv(path)
    assert graph.edge_count == 1


def test_header_whitespace_tolerant(tmp_path: Path) -> None:
    """Header names may contain surrounding whitespace."""
    path = tmp_path / "in.csv"
    _write(path, " source , target \n1,2\n")

    graph = import_csv(path)
    assert graph.edge_count == 1


def test_missing_source_column_raises(tmp_path: Path) -> None:
    """A header without 'source' raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "target,weight\n2,1.0\n")

    with pytest.raises(CsvFormatError, match="source"):
        import_csv(path)


def test_missing_target_column_raises(tmp_path: Path) -> None:
    """A header without 'target' raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "source,weight\n1,1.0\n")

    with pytest.raises(CsvFormatError, match="target"):
        import_csv(path)


def test_invalid_source_raises(tmp_path: Path) -> None:
    """A non-integer source value raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "source,target\nabc,2\n")

    with pytest.raises(CsvFormatError, match="source"):
        import_csv(path)


def test_invalid_target_raises(tmp_path: Path) -> None:
    """A non-integer target value raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "source,target\n1,abc\n")

    with pytest.raises(CsvFormatError, match="target"):
        import_csv(path)


def test_invalid_weight_raises(tmp_path: Path) -> None:
    """A non-numeric weight raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,weight\n1,2,abc\n")

    with pytest.raises(CsvFormatError, match="weight"):
        import_csv(path)


def test_invalid_directed_raises(tmp_path: Path) -> None:
    """An unrecognized directed value raises CsvFormatError."""
    path = tmp_path / "in.csv"
    _write(path, "source,target,directed\n1,2,maybe\n")

    with pytest.raises(CsvFormatError, match="directed"):
        import_csv(path)


def test_parallel_edges_are_preserved(tmp_path: Path) -> None:
    """Two rows between the same nodes produce two edges."""
    path = tmp_path / "in.csv"
    _write(
        path,
        "source,target,weight,directed\n1,2,1.0,false\n1,2,5.0,false\n",
    )

    graph = import_csv(path)
    assert graph.edge_count == 2
