"""Write a graph to the Graphviz DOT format."""

from pathlib import Path

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node

INDENT = "    "


def export_dot(graph: Graph, path: Path) -> None:
    """Write the graph to a DOT file.

    The format is chosen by content: if the graph has at least one
    directed edge, the output is a ``digraph``; otherwise it is a
    ``graph``. In a ``digraph`` undirected edges receive the
    attribute ``dir=none`` so that Graphviz renders them without
    arrowheads. This preserves mixed directed and undirected edges
    within a single document.

    Node labels are written when non-empty. Edge weights are written
    both as ``label`` (shown in the rendered output) and as
    ``weight`` (used by Graphviz for layout). Isolated nodes appear
    as standalone statements so that they are not dropped.

    Args:
        graph: The graph to export.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    path.write_text(render_dot(graph), encoding="utf-8")


def render_dot(graph: Graph) -> str:
    """Render the graph as a DOT document.

    Args:
        graph: The graph to render.

    Returns:
        A string containing a complete DOT document terminated by a
        newline.
    """
    edges = graph.edges()
    has_directed = any(edge.directed for edge in edges)
    header = "digraph G {" if has_directed else "graph G {"
    lines: list[str] = [header]
    for node in sorted(graph.nodes(), key=lambda n: n.id):
        lines.append(INDENT + _node_statement(node))
    for edge in sorted(edges, key=lambda e: (e.source, e.target)):
        lines.append(INDENT + _edge_statement(edge, has_directed))
    lines.append("}")
    return "\n".join(lines) + "\n"


def _node_statement(node: Node) -> str:
    if not node.label:
        return f"{node.id};"
    return f'{node.id} [label="{_escape(node.label)}"];'


def _edge_statement(edge: Edge, has_directed: bool) -> str:
    arrow = "->" if has_directed else "--"
    attributes: list[str] = []
    if has_directed and not edge.directed:
        attributes.append("dir=none")
    weight = f"{edge.weight:g}"
    attributes.append(f'label="{weight}"')
    attributes.append(f'weight="{weight}"')
    joined = ", ".join(attributes)
    return f"{edge.source} {arrow} {edge.target} [{joined}];"


def _escape(text: str) -> str:
    """Escape a string for inclusion inside DOT double quotes.

    Args:
        text: The raw text.

    Returns:
        Text with backslashes and quotes escaped and newlines
        flattened to spaces.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
