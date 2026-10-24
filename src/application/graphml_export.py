"""Write a graph to the GraphML XML format."""

from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node

GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
KEY_LABEL = "d0"
KEY_WEIGHT = "d1"
INDENT = "  "


def export_graphml(graph: Graph, path: Path) -> None:
    """Write the graph to a GraphML file.

    The output uses a single ``graph`` element with
    ``edgedefault="undirected"``. Directed edges carry
    ``directed="true"`` on the edge element, which is the standard
    way to represent mixed graphs in GraphML.

    Node ids in GraphML are strings. This module prefixes them with
    ``n`` (so node 1 becomes ``n1``) to avoid collisions with the
    schema's string type and to keep the output predictable.

    Node labels are stored under a ``label`` data key when non-empty.
    Edge weights are stored under a ``weight`` data key for every
    edge.

    Args:
        graph: The graph to export.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    path.write_text(render_graphml(graph), encoding="utf-8")


def render_graphml(graph: Graph) -> str:
    """Render the graph as a GraphML document.

    Args:
        graph: The graph to render.

    Returns:
        A string containing a complete GraphML document terminated
        by a newline.
    """
    lines: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(f"<graphml xmlns={quoteattr(GRAPHML_NAMESPACE)}>")
    lines.append(
        f'{INDENT}<key id={quoteattr(KEY_LABEL)} for="node" '
        f'attr.name="label" attr.type="string"/>'
    )
    lines.append(
        f'{INDENT}<key id={quoteattr(KEY_WEIGHT)} for="edge" '
        f'attr.name="weight" attr.type="double"/>'
    )
    lines.append(f'{INDENT}<graph id="G" edgedefault="undirected">')
    for node in sorted(graph.nodes(), key=lambda n: n.id):
        lines.extend(_render_node(node))
    for edge in sorted(graph.edges(), key=lambda e: (e.source, e.target)):
        lines.extend(_render_edge(edge))
    lines.append(f"{INDENT}</graph>")
    lines.append("</graphml>")
    return "\n".join(lines) + "\n"


def _render_node(node: Node) -> list[str]:
    node_id = f"n{node.id}"
    attributes = f"id={quoteattr(node_id)}"
    if not node.label:
        return [f"{INDENT * 2}<node {attributes}/>"]
    body = escape(node.label)
    return [
        f"{INDENT * 2}<node {attributes}>",
        f"{INDENT * 3}<data key={quoteattr(KEY_LABEL)}>{body}</data>",
        f"{INDENT * 2}</node>",
    ]


def _render_edge(edge: Edge) -> list[str]:
    source = f"n{edge.source}"
    target = f"n{edge.target}"
    attributes = f"source={quoteattr(source)} target={quoteattr(target)}"
    if edge.directed:
        attributes += ' directed="true"'
    weight = f"{edge.weight:g}"
    return [
        f"{INDENT * 2}<edge {attributes}>",
        f"{INDENT * 3}<data key={quoteattr(KEY_WEIGHT)}>{weight}</data>",
        f"{INDENT * 2}</edge>",
    ]
