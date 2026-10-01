"""Canvas widget that renders a graph using matplotlib."""

import math
from collections.abc import Callable
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch

from domain.entities.graph import Graph
from domain.value_objects.position import Position

ClickCallback = Callable[[float, float, int | None, tuple[int, int] | None], None]
DragMoveCallback = Callable[[float, float], None]
DragEndCallback = Callable[[], None]

NODE_HIT_RADIUS = 0.05
EDGE_HIT_RADIUS = 0.02
NODE_VISUAL_RADIUS = 0.025

COLOR_DEFAULT = "#1f77b4"
COLOR_HIGHLIGHTED = "#ff7f0e"
COLOR_CURRENT = "#d62728"
COLOR_EDGE = "#888888"

ARROW_MUTATION_SCALE = 14
CURRENT_BORDER_WIDTH = 2.5


class GraphCanvas(FigureCanvasQTAgg):
    """A matplotlib canvas displaying a graph.

    Positions are expected in the unit square (0..1); the canvas maps
    them to its axes without knowing about pixels. The canvas does not
    own the graph or its positions — it reads them on every draw and
    remembers the last drawn state only to resolve clicks to node ids
    and edges.

    Node fill colors come from the algorithm's step result, if any.
    When a node has no explicit color, the canvas falls back to its
    default palette: orange for visited nodes, red for the current
    node, blue otherwise. A node that has an explicit color keeps it
    even when it is the current node; the current node is highlighted
    with a thicker red border instead.

    Directed edges are drawn with an arrow head near the target node.
    The line is shortened by NODE_VISUAL_RADIUS at the target end so
    that the arrow head is not hidden under the node marker. Hit
    testing always uses the full segment between node centers, so
    clicking near a node still resolves to the node (node hits take
    priority over edge hits).

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
        node_colors: dict[int, str] | None = None,
    ) -> None:
        """Render the graph on the canvas.

        Args:
            graph: The graph to render.
            positions: Mapping from node id to position.
            highlighted_nodes: Ids of nodes to emphasize.
            current_node: Id of the node to draw as the current one.
            highlighted_edges: Edges to emphasize.
            labels: Optional per-node text labels.
            node_colors: Optional per-node fill colors as hex strings.
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
            node_colors or {},
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
            if edge.directed:
                self._draw_directed_edge(start, end, color, width)
            else:
                self._draw_undirected_edge(start, end, color, width)
            self._draw_edge_weight(edge.weight, start, end)

    def _draw_undirected_edge(
        self,
        start: Position,
        end: Position,
        color: str,
        width: float,
    ) -> None:
        self._axes.plot(
            [start.x, end.x],
            [start.y, end.y],
            color=color,
            linewidth=width,
            zorder=1,
        )

    def _draw_directed_edge(
        self,
        start: Position,
        end: Position,
        color: str,
        width: float,
    ) -> None:
        shortened_end = _shorten_towards(start, end, NODE_VISUAL_RADIUS)
        arrow = FancyArrowPatch(
            (start.x, start.y),
            (shortened_end.x, shortened_end.y),
            arrowstyle="->",
            mutation_scale=ARROW_MUTATION_SCALE,
            color=color,
            linewidth=width,
            shrinkA=0.0,
            shrinkB=0.0,
            zorder=1,
        )
        self._axes.add_patch(arrow)

    def _draw_edge_weight(
        self,
        weight: float,
        start: Position,
        end: Position,
    ) -> None:
        mid_x = (start.x + end.x) / 2.0
        mid_y = (start.y + end.y) / 2.0
        self._axes.text(
            mid_x,
            mid_y,
            f"{weight:g}",
            ha="center",
            va="center",
            color="black",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": "none",
            },
            zorder=1.5,
        )

    def _draw_nodes(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted: frozenset[int],
        current: int | None,
        labels: dict[int, str],
        node_colors: dict[int, str],
    ) -> None:
        for node in graph.nodes():
            if node.id not in positions:
                continue
            position = positions[node.id]
            fill_color = self._resolve_fill_color(
                node.id, highlighted, current, node_colors
            )
            is_current = node.id == current
            border_color = COLOR_CURRENT if is_current else "black"
            border_width = CURRENT_BORDER_WIDTH if is_current else 1.0
            self._axes.plot(
                position.x,
                position.y,
                marker="o",
                markersize=22,
                markerfacecolor=fill_color,
                markeredgecolor=border_color,
                markeredgewidth=border_width,
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

    @staticmethod
    def _resolve_fill_color(
        node_id: int,
        highlighted: frozenset[int],
        current: int | None,
        node_colors: dict[int, str],
    ) -> str:
        if node_id in node_colors:
            return node_colors[node_id]
        if node_id == current:
            return COLOR_CURRENT
        if node_id in highlighted:
            return COLOR_HIGHLIGHTED
        return COLOR_DEFAULT

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
        of the segment connecting its endpoints. The segment used for
        hit testing always runs between node centers, regardless of
        whether the edge is drawn with a shortened arrow head.

        The closest edge wins when several are within range.

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


def _shorten_towards(
    start: Position,
    end: Position,
    distance: float,
) -> Position:
    """Return a point on the segment closer to start by a fixed distance.

    Args:
        start: The anchor point that stays fixed.
        end: The point being pulled back towards start.
        distance: How far to move from end towards start.

    Returns:
        A new position between start and end, at the given distance
        from end. If the segment is shorter than the requested
        distance, returns start.
    """
    total = math.hypot(end.x - start.x, end.y - start.y)
    if total <= distance:
        return start
    ratio = (total - distance) / total
    return Position(
        x=start.x + (end.x - start.x) * ratio,
        y=start.y + (end.y - start.y) * ratio,
    )
