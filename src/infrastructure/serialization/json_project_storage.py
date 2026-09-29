"""JSON implementation of the ProjectStorage contract."""

import json
from pathlib import Path
from typing import Any

from application.project_storage import ProjectStorage, ProjectStorageError
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node
from domain.value_objects.position import Position

FORMAT_VERSION = 1
DEFAULT_POSITION = Position(x=0.5, y=0.5)


class JsonProjectStorage(ProjectStorage):
    """Stores a graph project as a JSON document.

    The format is a single object with a version field, a list of
    nodes (each with id, label, and position), and a list of edges
    (each with source, target, weight, and direction flag). The
    version field allows future format changes without breaking
    existing files.
    """

    def save(
        self,
        graph: Graph,
        positions: dict[int, Position],
        path: Path,
    ) -> None:
        """Write the project to the given path.

        Args:
            graph: The graph to save.
            positions: Node positions in the unit square.
            path: Destination file path.

        Raises:
            ProjectStorageError: If the project cannot be written.
        """
        data = self._to_dict(graph, positions)
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ProjectStorageError(f"Cannot write {path}: {exc}") from exc

    def load(self, path: Path) -> tuple[Graph, dict[int, Position]]:
        """Read the project from the given path.

        Args:
            path: Source file path.

        Returns:
            A tuple of the graph and its node positions.

        Raises:
            ProjectStorageError: If the project cannot be read.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProjectStorageError(f"Cannot read {path}: {exc}") from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectStorageError(f"Invalid JSON in {path}: {exc}") from exc
        return self._from_dict(data, path)

    def _to_dict(
        self,
        graph: Graph,
        positions: dict[int, Position],
    ) -> dict[str, Any]:
        nodes = []
        for node in graph.nodes():
            position = positions.get(node.id, DEFAULT_POSITION)
            nodes.append(
                {
                    "id": node.id,
                    "label": node.label,
                    "x": position.x,
                    "y": position.y,
                }
            )
        edges = []
        for edge in graph.edges():
            edges.append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight,
                    "directed": edge.directed,
                }
            )
        return {
            "version": FORMAT_VERSION,
            "nodes": nodes,
            "edges": edges,
        }

    def _from_dict(
        self,
        data: Any,
        path: Path,
    ) -> tuple[Graph, dict[int, Position]]:
        if not isinstance(data, dict):
            raise ProjectStorageError(f"{path}: top-level value must be an object")
        version = data.get("version")
        if version != FORMAT_VERSION:
            raise ProjectStorageError(f"{path}: unsupported version {version!r}")

        graph = Graph()
        positions: dict[int, Position] = {}
        try:
            for raw in data.get("nodes", []):
                node = Node(
                    id=int(raw["id"]),
                    label=str(raw.get("label", "")),
                )
                graph.add_node(node)
                positions[node.id] = Position(
                    x=float(raw["x"]),
                    y=float(raw["y"]),
                )
            for raw in data.get("edges", []):
                graph.add_edge(
                    Edge(
                        source=int(raw["source"]),
                        target=int(raw["target"]),
                        weight=float(raw.get("weight", 1.0)),
                        directed=bool(raw.get("directed", False)),
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectStorageError(f"{path}: malformed project data: {exc}") from exc
        return graph, positions
