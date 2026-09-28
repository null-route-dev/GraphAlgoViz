"""Canvas widget that renders a graph using matplotlib."""

import math
from collections.abc import Callable
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from domain.entities.graph import Graph
from domain.value_objects.position import Position

ClickCallback = Callable[[float, float, int | None, tuple[int, int] | None], None]
DragMoveCallback = Callable[[float, float], None]
DragEndCallback = Callable[[], None]

NODE_HIT_RADIUS = 0.05
EDGE_HIT_RADIUS = 0.02

COLOR_DEFAULT = "#1f77b4"
COLOR_HIGHLIGHTED = "#ff7f0e"
COLOR_CURRENT = "#d62728"
COLOR_EDGE = "#888888"


class GraphCanvas(FigureCanvasQTAgg):
    """A matplotlib canvas displaying a graph.

    Positions are expected in the unit square (0..1); the canvas maps
    them to its axes without knowing about pixels. The canvas does not
    own the graph or its positions — it reads them on every draw and
    remembers the last drawn state only to resolve clicks to node ids
    and edges.

    The canvas reports three kinds of mouse activity:

    - a left button press, with the coordinates, the id of the node
      under the cursor (or None), and the edge under the cursor as a
      (source, target) pair (or None). A node hit takes priority over
      an edge hit at the same point;
    - mouse motion while the left button is held down over a node that
      was under the cursor at press time;
    - the release of the left button.

    The canvas does not interpret these events. Deciding whether a
    drag is meaningful, and in which mode, is the caller's concern.

    Args:
        parent: Optional Qt parent widget.
        on_click: Optional callback invoked on left button press.
        on_drag_move: Optional callback invoked on mouse motion while
            the left button is held down after a press over a node.
        on_drag_end: Optional callback invoked on left button release.
    """

    def __init__(
        self,
        parent: object | None = None,
        on_click: ClickCallback | None = None,
        on_drag_move: DragMoveCallback | None = None,
        on_drag_end: DragEndCallback | None = None,
    ) -> None:
        self._figure = Figure(figsize=(6, 6), tight_layout=True)
        self._axes = self._figure.add_subplot(111)
        super().__init__(self._figure)
        if parent is not None:
            self.setParent(parent)  # type: ignore[arg-type]
        self._configure_axes()
        self._on_click = on_click
        self._on_drag_move = on_drag_move
        self._on_drag_end = on_drag_end
        self._last_graph: Graph | None = None
        self._last_positions: dict[int, Position] = {}
        self._pressed_node: int | None = None
        self.mpl_connect("button_press_event", self._handle_press)
        self.mpl_connect("motion_notify_event", self._handle_motion)
        self.mpl_connect("button_release_event", self._handle_release)

    def _configure_axes(self) -> None:
        """Set up axes limits and appearance."""
        self._axes.set_xlim(0.0, 1.0)
        self._axes.set_ylim(0.0, 1.0)
        self._axes.set_aspect("equal")
        self._axes.axis("off")

    def draw_graph(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted_nodes: frozenset[int] = frozenset(),
        current_node: int | None = None,
        highlighted_edges: frozenset[tuple[int, int]] = frozenset(),
        labels: dict[int, str] | None = None,
    ) -> None:
        """Render the graph on the canvas.

        Args:
            graph: The graph to render.
            positions: Mapping from node id to position.
            highlighted_nodes: Ids of nodes to emphasize.
            current_node: Id of the node to draw as the current one.
            highlighted_edges: Edges to emphasize.
            labels: Optional per-node text labels.
        """
        self._last_graph = graph
        self._last_positions = dict(positions)
        self._axes.clear()
        self._configure_axes()
        self._draw_edges(graph, positions, highlighted_edges)
        self._draw_nodes(
            graph,
            positions,
            highlighted_nodes,
            current_node,
            labels or {},
        )
        self.draw()

    def _draw_edges(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted: frozenset[tuple[int, int]],
    ) -> None:
        for edge in graph.edges():
            if edge.source not in positions or edge.target not in positions:
                continue
            start = positions[edge.source]
            end = positions[edge.target]
            is_highlighted = (edge.source, edge.target) in highlighted or (
                edge.target,
                edge.source,
            ) in highlighted
            color = COLOR_CURRENT if is_highlighted else COLOR_EDGE
            width = 2.5 if is_highlighted else 1.0
            self._axes.plot(
                [start.x, end.x],
                [start.y, end.y],
                color=color,
                linewidth=width,
                zorder=1,
            )

    def _draw_nodes(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted: frozenset[int],
        current: int | None,
        labels: dict[int, str],
    ) -> None:
        for node in graph.nodes():
            if node.id not in positions:
                continue
            position = positions[node.id]
            if node.id == current:
                color = COLOR_CURRENT
            elif node.id in highlighted:
                color = COLOR_HIGHLIGHTED
            else:
                color = COLOR_DEFAULT
            self._axes.plot(
                position.x,
                position.y,
                marker="o",
                markersize=22,
                markerfacecolor=color,
                markeredgecolor="black",
                markeredgewidth=1.0,
                zorder=2,
            )
            self._axes.text(
                position.x,
                position.y,
                str(node.id),
                ha="center",
                va="center",
                color="white",
                fontsize=10,
                zorder=3,
            )
            if node.id in labels:
                self._axes.text(
                    position.x,
                    position.y + 0.06,
                    labels[node.id],
                    ha="center",
                    va="bottom",
                    color="black",
                    fontsize=9,
                    zorder=3,
                )

    def _handle_press(self, event: Any) -> None:
        """Handle a left mouse press.

        Args:
            event: A matplotlib mouse event.
        """
        if event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        x = float(event.xdata)
        y = float(event.ydata)
        node_id = self._find_node_at(x, y)
        edge = None if node_id is not None else self._find_edge_at(x, y)
        self._pressed_node = node_id
        if self._on_click is not None:
            self._on_click(x, y, node_id, edge)

    def _handle_motion(self, event: Any) -> None:
        """Handle mouse motion while the left button is held down.

        Args:
            event: A matplotlib mouse event.
        """
        if event.button != 1:
            return
        if self._pressed_node is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        if self._on_drag_move is not None:
            self._on_drag_move(float(event.xdata), float(event.ydata))

    def _handle_release(self, event: Any) -> None:
        """Handle the release of the left mouse button.

        Args:
            event: A matplotlib mouse event.
        """
        if event.button != 1:
            return
        self._pressed_node = None
        if self._on_drag_end is not None:
            self._on_drag_end()

    def _find_node_at(self, x: float, y: float) -> int | None:
        """Return the id of the node closest to the given point.

        A node counts as hit if its center lies within NODE_HIT_RADIUS
        of the point in unit coordinates. The closest node wins when
        several are within range.

        Args:
            x: Horizontal coordinate of the point.
            y: Vertical coordinate of the point.

        Returns:
            The id of the closest node within range, or None.
        """
        if self._last_graph is None:
            return None
        best_id: int | None = None
        best_distance = NODE_HIT_RADIUS
        for node in self._last_graph.nodes():
            position = self._last_positions.get(node.id)
            if position is None:
                continue
            distance = math.hypot(position.x - x, position.y - y)
            if distance < best_distance:
                best_distance = distance
                best_id = node.id
        return best_id

    def _find_edge_at(self, x: float, y: float) -> tuple[int, int] | None:
        """Return the endpoints of the edge closest to the given point.

        An edge counts as hit if the point lies within EDGE_HIT_RADIUS
        of the segment connecting its endpoints. The closest edge wins
        when several are within range.

        Args:
            x: Horizontal coordinate of the point.
            y: Vertical coordinate of the point.

        Returns:
            The (source, target) pair of the closest edge within
            range, or None.
        """
        if self._last_graph is None:
            return None
        best_edge: tuple[int, int] | None = None
        best_distance = EDGE_HIT_RADIUS
        for edge in self._last_graph.edges():
            start = self._last_positions.get(edge.source)
            end = self._last_positions.get(edge.target)
            if start is None or end is None:
                continue
            distance = _point_to_segment_distance(x, y, start.x, start.y, end.x, end.y)
            if distance < best_distance:
                best_distance = distance
                best_edge = (edge.source, edge.target)
        return best_edge


def _point_to_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """Return the distance from a point to a line segment.

    Args:
        px: Horizontal coordinate of the point.
        py: Vertical coordinate of the point.
        x1: Horizontal coordinate of the segment start.
        y1: Vertical coordinate of the segment start.
        x2: Horizontal coordinate of the segment end.
        y2: Vertical coordinate of the segment end.

    Returns:
        The Euclidean distance from the point to the closest point
        on the segment.
    """
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)
