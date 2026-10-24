"""Tests for the GraphML graph exporter."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from application.graphml_export import (
    GRAPHML_NAMESPACE,
    KEY_LABEL,
    KEY_WEIGHT,
    export_graphml,
    render_graphml,
)
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node

NS = {"g": GRAPHML_NAMESPACE}


def _parse(text: str) -> ElementTree.Element:
    return ElementTree.fromstring(text)


def test_empty_graph_is_valid_xml() -> None:
    """An empty graph produces a well-formed GraphML document."""
    root = _parse(render_graphml(Graph()))

    assert root.tag == f"{{{GRAPHML_NAMESPACE}}}graphml"


def test_empty_graph_has_no_nodes_or_edges() -> None:
    """An empty graph contains an empty graph element."""
    root = _parse(render_graphml(Graph()))
    graph = root.find("g:graph", NS)

    assert graph is not None
    assert graph.findall("g:node", NS) == []
    assert graph.findall("g:edge", NS) == []


def test_graph_element_declares_undirected_default() -> None:
    """The graph element uses undirected as its default edge kind."""
    root = _parse(render_graphml(Graph()))
    graph = root.find("g:graph", NS)

    assert graph is not None
    assert graph.get("edgedefault") == "undirected"


def test_single_node_is_present() -> None:
    """A single node appears with an n-prefixed id."""
    graph = Graph()
    graph.add_node(Node(id=1))

    root = _parse(render_graphml(graph))
    nodes = root.findall("g:graph/g:node", NS)

    assert len(nodes) == 1
    assert nodes[0].get("id") == "n1"


def test_node_without_label_has_no_data() -> None:
    """A node with an empty label has no data child."""
    graph = Graph()
    graph.add_node(Node(id=1))

    root = _parse(render_graphml(graph))
    node = root.find("g:graph/g:node", NS)

    assert node is not None
    assert node.findall("g:data", NS) == []


def test_node_label_is_written() -> None:
    """A non-empty label appears as a data element."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A"))

    root = _parse(render_graphml(graph))
    data = root.find(f"g:graph/g:node/g:data[@key='{KEY_LABEL}']", NS)

    assert data is not None
    assert data.text == "A"


def test_undirected_edge_is_written() -> None:
    """An undirected edge has no directed attribute."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=1.5))

    root = _parse(render_graphml(graph))
    edge = root.find("g:graph/g:edge", NS)

    assert edge is not None
    assert edge.get("source") == "n1"
    assert edge.get("target") == "n2"
    assert edge.get("directed") is None
    weight = edge.find(f"g:data[@key='{KEY_WEIGHT}']", NS)
    assert weight is not None
    assert weight.text == "1.5"


def test_directed_edge_has_directed_attribute() -> None:
    """A directed edge carries directed=true."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, directed=True))

    root = _parse(render_graphml(graph))
    edge = root.find("g:graph/g:edge", NS)

    assert edge is not None
    assert edge.get("directed") == "true"


def test_integer_weight_has_no_decimal_point() -> None:
    """Integer weights are formatted without a trailing .0."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=3.0))

    root = _parse(render_graphml(graph))
    weight = root.find(f"g:graph/g:edge/g:data[@key='{KEY_WEIGHT}']", NS)

    assert weight is not None
    assert weight.text == "3"


def test_self_loop_is_written() -> None:
    """A self-loop appears as an edge from the node to itself."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_edge(Edge(source=1, target=1))

    root = _parse(render_graphml(graph))
    edges = root.findall("g:graph/g:edge", NS)

    assert len(edges) == 1
    assert edges[0].get("source") == "n1"
    assert edges[0].get("target") == "n1"


def test_label_with_ampersand_is_escaped() -> None:
    """Ampersands in labels survive the XML parser."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A & B"))

    root = _parse(render_graphml(graph))
    data = root.find(f"g:graph/g:node/g:data[@key='{KEY_LABEL}']", NS)

    assert data is not None
    assert data.text == "A & B"


def test_label_with_angle_brackets_is_escaped() -> None:
    """Angle brackets in labels survive the XML parser."""
    graph = Graph()
    graph.add_node(Node(id=1, label="<x>"))

    root = _parse(render_graphml(graph))
    data = root.find(f"g:graph/g:node/g:data[@key='{KEY_LABEL}']", NS)

    assert data is not None
    assert data.text == "<x>"


def test_nodes_are_sorted_by_id() -> None:
    """Node elements appear in ascending id order."""
    graph = Graph()
    for node_id in (3, 1, 2):
        graph.add_node(Node(id=node_id))

    root = _parse(render_graphml(graph))
    ids = [node.get("id") for node in root.findall("g:graph/g:node", NS)]

    assert ids == ["n1", "n2", "n3"]


def test_edges_are_sorted_by_endpoints() -> None:
    """Edge elements appear sorted by (source, target)."""
    graph = Graph()
    for node_id in (1, 2, 3):
        graph.add_node(Node(id=node_id))
    graph.add_edge(Edge(source=2, target=3))
    graph.add_edge(Edge(source=1, target=2))

    root = _parse(render_graphml(graph))
    edges = root.findall("g:graph/g:edge", NS)

    assert edges[0].get("source") == "n1"
    assert edges[1].get("source") == "n2"


def test_render_is_deterministic() -> None:
    """Two calls with the same graph produce identical output."""
    graph = Graph()
    graph.add_node(Node(id=1, label="A"))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2, weight=2.5))

    assert render_graphml(graph) == render_graphml(graph)


def test_two_keys_are_declared() -> None:
    """Both label and weight keys are declared in the document."""
    root = _parse(render_graphml(Graph()))
    keys = root.findall("g:key", NS)
    ids = {key.get("id") for key in keys}

    assert ids == {KEY_LABEL, KEY_WEIGHT}


def test_export_writes_file(tmp_path: Path) -> None:
    """Exporting to a file writes a parseable GraphML document."""
    graph = Graph()
    graph.add_node(Node(id=1))
    graph.add_node(Node(id=2))
    graph.add_edge(Edge(source=1, target=2))
    path = tmp_path / "graph.graphml"

    export_graphml(graph, path)

    assert path.exists()
    root = _parse(path.read_text(encoding="utf-8"))
    assert root.tag == f"{{{GRAPHML_NAMESPACE}}}graphml"


def test_export_fails_on_missing_directory(tmp_path: Path) -> None:
    """A non-existent directory raises OSError."""
    with pytest.raises(OSError):
        export_graphml(Graph(), tmp_path / "missing" / "out.graphml")
