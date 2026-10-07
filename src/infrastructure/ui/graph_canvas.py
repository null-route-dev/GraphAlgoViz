"""Canvas widget that renders a graph using matplotlib."""

import math
from collections.abc import Callable
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
from PySide6.QtCore import QTimer

from domain.entities.edge import Edge
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

ARROW_MUTATION_SCALE = 14
CURRENT_BORDER_WIDTH = 2.5

TRANSITION_FRAME_MS = 20
TRANSITION_STEP = 0.18

ARC_SPACING = 0.18

DARK_BG = "#1e1e1e"
DARK_NODE_BORDER = "#cccccc"
DARK_EDGE = "#aaaaaa"
DARK_NODE_LABEL = "#ffffff"
DARK_WEIGHT_TEXT = "#ffffff"
DARK_WEIGHT_BG = "#2b2b2b"

LIGHT_BG = "#ffffff"
LIGHT_NODE_BORDER = "#000000"
LIGHT_EDGE = "#888888"
LIGHT_NODE_LABEL = "#000000"
LIGHT_WEIGHT_TEXT = "#000000"
LIGHT_WEIGHT_BG = "#ffffff"


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

    A single edge may be marked as current in the step result. That
    edge is drawn with a dashed line in the highlighted color to show
    that the algorithm is considering it right now.

    Edges between the same pair of nodes are drawn as arcs. When only
    one edge connects two nodes, it is drawn as a straight line. When
    several edges share the same pair of endpoints, they are bent by
    different amounts so that they do not overlap. Directed and
    undirected edges share the same slot allocation, so a directed
    edge and its reverse remain visually distinct.

    The canvas supports a dark and a light theme.

    Color changes are animated. When a new draw request arrives with
    different fill colors, the canvas interpolates each node's color
    over several frames.

    Args:
        parent: Optional Qt parent widget.
        on_click: Optional callback invoked on left button press.
        on_drag_move: Optional callback invoked on mouse motion while
            the left button is held down after a press over a node.
        on_drag_end: Optional callback invoked on left button release.
        dark: Whether to start with the dark theme.
    """

    def __init__(
        self,
        parent: object | None = None,
        on_click: ClickCallback | None = None,
        on_drag_move: DragMoveCallback | None = None,
        on_drag_end: DragEndCallback | None = None,
        dark: bool = True,
    ) -> None:
        self._figure = Figure(figsize=(6, 6), tight_layout=True)
        self._axes = self._figure.add_subplot(111)
        super().__init__(self._figure)
        if parent is not None:
            self.setParent(parent)  # type: ignore[arg-type]

        self._dark = dark
        self._bg_color = DARK_BG if dark else LIGHT_BG
        self._node_border_color = DARK_NODE_BORDER if dark else LIGHT_NODE_BORDER
        self._edge_color = DARK_EDGE if dark else LIGHT_EDGE
        self._node_label_color = DARK_NODE_LABEL if dark else LIGHT_NODE_LABEL
        self._weight_text_color = DARK_WEIGHT_TEXT if dark else LIGHT_WEIGHT_TEXT
        self._weight_bg_color = DARK_WEIGHT_BG if dark else LIGHT_WEIGHT_BG

        self._configure_axes()

        self._on_click = on_click
        self._on_drag_move = on_drag_move
        self._on_drag_end = on_drag_end

        self._last_graph: Graph | None = None
        self._last_positions: dict[int, Position] = {}
        self._last_highlighted_nodes: frozenset[int] = frozenset()
        self._last_current_node: int | None = None
        self._last_current_edge: tuple[int, int] | None = None
        self._last_highlighted_edges: frozenset[tuple[int, int]] = frozenset()
        self._last_labels: dict[int, str] = {}

        self._colors_start: dict[int, str] = {}
        self._colors_target: dict[int, str] = {}
        self._colors_displayed: dict[int, str] = {}
        self._transition_progress = 1.0

        self._transition_timer = QTimer(self)
        self._transition_timer.setInterval(TRANSITION_FRAME_MS)
        self._transition_timer.timeout.connect(self._on_transition_tick)

        self._pressed_node: int | None = None
        self.mpl_connect("button_press_event", self._handle_press)
        self.mpl_connect("motion_notify_event", self._handle_motion)
        self.mpl_connect("button_release_event", self._handle_release)

    def set_dark(self, dark: bool) -> None:
        """Switch between the dark and light themes.

        Args:
            dark: True for the dark theme, False for the light theme.
        """
        if dark == self._dark:
            return
        self._dark = dark
        self._bg_color = DARK_BG if dark else LIGHT_BG
        self._node_border_color = DARK_NODE_BORDER if dark else LIGHT_NODE_BORDER
        self._edge_color = DARK_EDGE if dark else LIGHT_EDGE
        self._node_label_color = DARK_NODE_LABEL if dark else LIGHT_NODE_LABEL
        self._weight_text_color = DARK_WEIGHT_TEXT if dark else LIGHT_WEIGHT_TEXT
        self._weight_bg_color = DARK_WEIGHT_BG if dark else LIGHT_WEIGHT_BG
        self._figure.patch.set_facecolor(self._bg_color)
        self._redraw()

    def _configure_axes(self) -> None:
        """Set up axes limits and appearance."""
        self._axes.set_xlim(0.0, 1.0)
        self._axes.set_ylim(0.0, 1.0)
        self._axes.set_aspect("equal")
        self._axes.axis("off")
        self._figure.patch.set_facecolor(self._bg_color)
        self._axes.set_facecolor(self._bg_color)

    def draw_graph(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted_nodes: frozenset[int] = frozenset(),
        current_node: int | None = None,
        highlighted_edges: frozenset[tuple[int, int]] = frozenset(),
        labels: dict[int, str] | None = None,
        node_colors: dict[int, str] | None = None,
        current_edge: tuple[int, int] | None = None,
    ) -> None:
        """Render the graph on the canvas with animated color changes.

        Args:
            graph: The graph to render.
            positions: Mapping from node id to position.
            highlighted_nodes: Ids of nodes to emphasize.
            current_node: Id of the node to draw as the current one.
            highlighted_edges: Edges to emphasize.
            labels: Optional per-node text labels.
            node_colors: Optional per-node fill colors as hex strings.
            current_edge: Optional edge to draw as the one being
                considered by the algorithm.
        """
        self._last_graph = graph
        self._last_positions = dict(positions)
        self._last_highlighted_nodes = highlighted_nodes
        self._last_current_node = current_node
        self._last_current_edge = current_edge
        self._last_highlighted_edges = highlighted_edges
        self._last_labels = dict(labels or {})

        new_targets: dict[int, str] = {}
        for node in graph.nodes():
            if node.id not in positions:
                continue
            new_targets[node.id] = self._resolve_fill_color(
                node.id,
                highlighted_nodes,
                current_node,
                node_colors or {},
            )

        if new_targets == self._colors_target and self._transition_timer.isActive():
            return

        self._transition_timer.stop()
        if self._colors_target:
            self._colors_displayed = dict(self._colors_target)

        self._colors_start = (
            dict(self._colors_displayed)
            if self._colors_displayed
            else dict(new_targets)
        )
        self._colors_target = new_targets

        if self._colors_start == self._colors_target:
            self._colors_displayed = dict(new_targets)
            self._transition_progress = 1.0
            self._redraw()
            return

        self._transition_progress = 0.0
        self._redraw()
        self._transition_timer.start()

    def _on_transition_tick(self) -> None:
        """Advance the color transition by one frame."""
        self._transition_progress = min(
            1.0, self._transition_progress + TRANSITION_STEP
        )
        t = self._transition_progress
        new_displayed: dict[int, str] = {}
        for node_id, target in self._colors_target.items():
            start = self._colors_start.get(node_id, target)
            new_displayed[node_id] = _lerp_color(start, target, t)
        self._colors_displayed = new_displayed
        if t >= 1.0:
            self._transition_timer.stop()
        self._redraw()

    def _redraw(self) -> None:
        """Redraw the canvas using the current displayed colors."""
        if self._last_graph is None:
            self._axes.clear()
            self._configure_axes()
            self.draw()
            return
        self._axes.clear()
        self._configure_axes()
        self._draw_edges(
            self._last_graph,
            self._last_positions,
            self._last_highlighted_edges,
            self._last_current_edge,
        )
        self._draw_nodes(
            self._last_graph,
            self._last_positions,
            self._last_highlighted_nodes,
            self._last_current_node,
            self._last_labels,
            self._colors_displayed,
        )
        self.draw()

    def _draw_edges(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted: frozenset[tuple[int, int]],
        current_edge: tuple[int, int] | None,
    ) -> None:
        groups = _group_edges_by_endpoints(graph.edges())
        for key, edges in groups.items():
            total = len(edges)
            for index, edge in enumerate(edges):
                if edge.source not in positions or edge.target not in positions:
                    continue
                start = positions[edge.source]
                end = positions[edge.target]
                is_highlighted = (edge.source, edge.target) in highlighted or (
                    edge.target,
                    edge.source,
                ) in highlighted
                is_current = current_edge is not None and (
                    (edge.source, edge.target) == current_edge
                    or (edge.target, edge.source) == current_edge
                )
                if is_current:
                    color = COLOR_HIGHLIGHTED
                    width = 2.5
                    linestyle = "--"
                elif is_highlighted:
                    color = COLOR_CURRENT
                    width = 2.5
                    linestyle = "-"
                else:
                    color = self._edge_color
                    width = 1.0
                    linestyle = "-"
                rad = _effective_rad(edge, key, _arc_rad_for_index(index, total))
                self._draw_edge(start, end, color, width, edge.directed, rad, linestyle)
                self._draw_edge_weight(edge.weight, start, end, rad)

    def _draw_edge(
        self,
        start: Position,
        end: Position,
        color: str,
        width: float,
        directed: bool,
        rad: float,
        linestyle: str,
    ) -> None:
        if rad == 0.0 and not directed and linestyle == "-":
            self._axes.plot(
                [start.x, end.x],
                [start.y, end.y],
                color=color,
                linewidth=width,
                linestyle=linestyle,
                zorder=1,
            )
            return

        if directed:
            shortened_end = _shorten_towards(start, end, NODE_VISUAL_RADIUS)
            tail = (start.x, start.y)
            head = (shortened_end.x, shortened_end.y)
            style = "->"
        else:
            tail = (start.x, start.y)
            head = (end.x, end.y)
            style = "-"

        arrow = FancyArrowPatch(
            tail,
            head,
            arrowstyle=style,
            mutation_scale=ARROW_MUTATION_SCALE,
            connectionstyle=f"arc3,rad={rad}",
            color=color,
            linewidth=width,
            linestyle=linestyle,
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
        rad: float,
    ) -> None:
        mid_x, mid_y = _arc_midpoint(start, end, rad)
        self._axes.text(
            mid_x,
            mid_y,
            f"{weight:g}",
            ha="center",
            va="center",
            color=self._weight_text_color,
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": self._weight_bg_color,
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
            fill_color = node_colors.get(
                node.id,
                self._resolve_fill_color(node.id, highlighted, current, node_colors),
            )
            is_current = node.id == current
            border_color = COLOR_CURRENT if is_current else self._node_border_color
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
                    color=self._node_label_color,
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
        whether the edge is drawn as a straight line or an arc.

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


def _group_edges_by_endpoints(
    edges: list[Edge],
) -> dict[tuple[int, int], list[Edge]]:
    """Group edges by their unordered pair of endpoints.

    Args:
        edges: The edges to group.

    Returns:
        A mapping from the sorted endpoint pair to the list of edges
        connecting those endpoints, in the original order.
    """
    groups: dict[tuple[int, int], list[Edge]] = {}
    for edge in edges:
        key = (min(edge.source, edge.target), max(edge.source, edge.target))
        groups.setdefault(key, []).append(edge)
    return groups


def _arc_rad_for_index(index: int, total: int) -> float:
    """Return the arc curvature for the given slot in a group.

    Args:
        index: Zero-based index of the edge within its group.
        total: Number of edges in the group.

    Returns:
        The signed curvature value for the edge.
    """
    if total <= 1:
        return 0.0
    return ARC_SPACING * (index - (total - 1) / 2.0)


def _effective_rad(
    edge: Edge,
    key: tuple[int, int],
    rad: float,
) -> float:
    """Return the curvature to use when drawing the edge.

    Args:
        edge: The edge being drawn.
        key: The sorted endpoint pair shared by the group.
        rad: The curvature for the edge's slot, relative to the
            canonical direction.

    Returns:
        The signed curvature to pass to the drawing routine.
    """
    if edge.source == key[0]:
        return rad
    return -rad


def _arc_midpoint(
    start: Position,
    end: Position,
    rad: float,
) -> tuple[float, float]:
    """Return the midpoint of an arc3 curve between two positions.

    Args:
        start: The start position of the edge.
        end: The end position of the edge.
        rad: The curvature value passed to arc3.

    Returns:
        A tuple (x, y) for the label position.
    """
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.hypot(dx, dy)
    mid_x = (start.x + end.x) / 2.0
    mid_y = (start.y + end.y) / 2.0
    if length == 0.0 or rad == 0.0:
        return mid_x, mid_y
    perp_x = -dy / length
    perp_y = dx / length
    return (
        mid_x + 0.5 * rad * perp_x * length,
        mid_y + 0.5 * rad * perp_y * length,
    )


def _lerp_color(start: str, end: str, t: float) -> str:
    """Interpolate between two hex colors.

    Args:
        start: Hex color string, for example "#1f77b4".
        end: Hex color string of the same format.
        t: Interpolation parameter in [0.0, 1.0]. 0 returns start,
            1 returns end, values in between produce a blend.

    Returns:
        A hex color string representing the interpolated color.
    """
    clamped = max(0.0, min(1.0, t))
    sr = int(start[1:3], 16)
    sg = int(start[3:5], 16)
    sb = int(start[5:7], 16)
    er = int(end[1:3], 16)
    eg = int(end[3:5], 16)
    eb = int(end[5:7], 16)
    r = round(sr + (er - sr) * clamped)
    g = round(sg + (eg - sg) * clamped)
    b = round(sb + (eb - sb) * clamped)
    return f"#{r:02x}{g:02x}{b:02x}"


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
