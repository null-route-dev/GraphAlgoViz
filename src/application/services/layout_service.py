"""Service for computing initial node positions."""

import math

from domain.entities.graph import Graph
from domain.value_objects.position import Position


class LayoutService:
    """Computes positions for graph nodes.

    Positions are expressed in a unit square (0..1) so that the
    presentation layer can map them to any canvas size without
    knowing about pixels.
    """

    def circular(self, graph: Graph) -> dict[int, Position]:
        """Place every node evenly on a circle.

        If the graph is empty, returns an empty mapping. If the graph
        has a single node, that node is placed at the center.

        Args:
            graph: The graph to lay out.

        Returns:
            A mapping from node id to position.
        """
        node_ids = [node.id for node in graph.nodes()]
        count = len(node_ids)
        if count == 0:
            return {}
        if count == 1:
            return {node_ids[0]: Position(x=0.5, y=0.5)}

        result: dict[int, Position] = {}
        for index, node_id in enumerate(node_ids):
            angle = 2.0 * math.pi * index / count
            x = 0.5 + 0.4 * math.cos(angle)
            y = 0.5 + 0.4 * math.sin(angle)
            result[node_id] = Position(x=x, y=y)
        return result
