"""Read a graph from a CSV edge list."""

import csv
from pathlib import Path

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node

DEFAULT_WEIGHT = 1.0
TRUE_VALUES = frozenset({"true", "1", "yes"})
FALSE_VALUES = frozenset({"false", "0", "no", ""})


class CsvFormatError(Exception):
    """Raised when a CSV file cannot be parsed as a graph edge list."""


def import_csv(path: Path) -> Graph:
    """Read a graph from a CSV file.

    The header row must contain ``source`` and ``target`` columns.
    Columns ``weight`` and ``directed`` are optional and default to
    ``1.0`` and ``false`` respectively. A data row with an empty
    target declares an isolated node; any other data row declares an
    edge and creates its endpoints if they do not exist yet.

    Node labels are not part of the format; imported nodes have empty
    labels.

    Args:
        path: Source file path.

    Returns:
        A new graph built from the file.

    Raises:
        OSError: If the file cannot be read.
        CsvFormatError: If the header is malformed or a data row
            contains an invalid value.
    """
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return Graph()
        columns = _parse_header(header)
        graph = Graph()
        row_number = 1
        for row in reader:
            row_number += 1
            _apply_row(graph, row, columns, row_number)
    return graph


def _parse_header(header: list[str]) -> dict[str, int]:
    normalized = [cell.strip().lower() for cell in header]
    for required in ("source", "target"):
        if required not in normalized:
            raise CsvFormatError(f"Missing required column '{required}' in header")
    return {name: index for index, name in enumerate(normalized)}


def _apply_row(
    graph: Graph,
    row: list[str],
    columns: dict[str, int],
    row_number: int,
) -> None:
    if not row or all(not cell.strip() for cell in row):
        return
    source = _parse_int(row, columns["source"], row_number, "source")
    if not graph.has_node(source):
        graph.add_node(Node(id=source))

    target_text = _get_cell(row, columns, "target")
    if not target_text:
        return

    target = _parse_int(row, columns["target"], row_number, "target")
    if not graph.has_node(target):
        graph.add_node(Node(id=target))

    weight = DEFAULT_WEIGHT
    weight_text = _get_cell(row, columns, "weight")
    if weight_text:
        try:
            weight = float(weight_text)
        except ValueError as exc:
            raise CsvFormatError(
                f"Row {row_number}: invalid weight '{weight_text}'"
            ) from exc

    directed = False
    directed_text = _get_cell(row, columns, "directed").lower()
    if directed_text:
        if directed_text not in TRUE_VALUES | FALSE_VALUES:
            raise CsvFormatError(
                f"Row {row_number}: invalid directed value '{directed_text}'"
            )
        directed = directed_text in TRUE_VALUES

    graph.add_edge(
        Edge(
            source=source,
            target=target,
            weight=weight,
            directed=directed,
        )
    )


def _get_cell(
    row: list[str],
    columns: dict[str, int],
    name: str,
) -> str:
    index = columns.get(name)
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _parse_int(
    row: list[str],
    index: int,
    row_number: int,
    column_name: str,
) -> int:
    try:
        return int(row[index].strip())
    except (IndexError, ValueError) as exc:
        raise CsvFormatError(f"Row {row_number}: invalid {column_name}") from exc
