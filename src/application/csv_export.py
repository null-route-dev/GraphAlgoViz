"""Write a graph to a CSV edge list."""

import csv
from pathlib import Path

from domain.entities.graph import Graph

CSV_HEADER = ("source", "target", "weight", "directed")
DIRECTED_TRUE = "true"
DIRECTED_FALSE = "false"


def export_csv(graph: Graph, path: Path) -> None:
    """Write the graph to a CSV file.

    The output has a fixed header row and one data row per edge. Rows
    for isolated nodes (nodes with no incident edges) use an empty
    target column; those nodes would otherwise be lost because the
    format describes edges, not nodes.

    Node labels are not part of the format and are lost on export.
    Directed flag is written as the strings ``true`` or ``false``.

    Args:
        graph: The graph to export.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    edges = graph.edges()
    nodes_with_edges: set[int] = set()
    for edge in edges:
        nodes_with_edges.add(edge.source)
        nodes_with_edges.add(edge.target)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for node in sorted(graph.nodes(), key=lambda n: n.id):
            if node.id in nodes_with_edges:
                continue
            writer.writerow((node.id, "", "", ""))
        for edge in edges:
            writer.writerow(
                (
                    edge.source,
                    edge.target,
                    f"{edge.weight:g}",
                    DIRECTED_TRUE if edge.directed else DIRECTED_FALSE,
                )
            )
