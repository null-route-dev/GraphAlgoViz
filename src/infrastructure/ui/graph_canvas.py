"""Canvas widget that renders a graph using matplotlib."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QToolTip

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.value_objects.position import Position


@dataclass(frozen=True)
class ClickEvent:
    """A left-button press on the canvas.

    Args:
        x: Horizontal coordinate in the unit square.
        y: Vertical coordinate in the unit square.
        node_id: Id of the node under the cursor, or None.
        edge: Endpoints of the edge under the cursor, or None.
        shift: Whether Shift was held.
        double: Whether this was the second click of a double-click.
    """

    x: float
    y: float
    node_id: int | None
    edge: tuple[int, int] | None
    shift: bool
    double: bool


@dataclass(frozen=True)
class ContextEvent:
    """A right-button press on the canvas.

    Args:
        x: Horizontal coordinate in the unit square.
        y: Vertical coordinate in the unit square.
        node_id: Id of the node under the cursor, or None.
        edge: Endpoints of the edge under the cursor, or None.
        global_x: Screen x coordinate for menu placement.
        global_y: Screen y coordinate for menu placement.
    """

    x: float
    y: float
    node_id: int | None
    edge: tuple[int, int] | None
    global_x: int
    global_y: int


@dataclass(frozen=True)
class SelectionEvent:
    """A completed rubber-band selection.

    Args:
        x1: Left edge of the selection in the unit square.
        y1: Bottom edge of the selection in the unit square.
        x2: Right edge of the selection in the unit square.
        y2: Top edge of the selection in the unit square.
        additive: Whether Shift was held when the selection started.
    """

    x1: float
    y1: float
    x2: float
    y2: float
    additive: bool


ClickCallback = Callable[[ClickEvent], None]
ContextCallback = Callable[[ContextEvent], None]
SelectionCallback = Callable[[SelectionEvent], None]
DragMoveCallback = Callable[[float, float], None]
DragEndCallback = Callable[[], None]

NODE_HIT_RADIUS = 0.05
EDGE_HIT_RADIUS = 0.02
NODE_VISUAL_RADIUS = 0.025

COLOR_DEFAULT = "#1f77b4"
COLOR_HIGHLIGHTED = "#ff7f0e"
COLOR_CURRENT = "#d62728"
COLOR_SELECTED = "#2ca02c"
SELECTED_BORDER_WIDTH = 3.5

ARROW_MUTATION_SCALE = 14
ARROW_MIDDLE_SEGMENT = 0.02
CURRENT_BORDER_WIDTH = 2.5

TRANSITION_FRAME_MS = 20
TRANSITION_STEP = 0.18

ARC_SPACING = 0.18

SELF_LOOP_BASE_RADIUS = 0.05
SELF_LOOP_STACK_STEP = 0.018
SELF_LOOP_BASE_OFFSET = 0.06
SELF_LOOP_STACK_OFFSET = 0.022
SELF_LOOP_LABEL_MARGIN = 0.02

BUNDLE_MIN_WIDTH = 1.0
BUNDLE_WIDTH_PER_EDGE = 0.6
BUNDLE_MAX_WIDTH = 4.0

SELECTION_FILL = "#1f77b4"
SELECTION_ALPHA = 0.15

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

DEFAULT_EXPORT_DPI = 200


class GraphCanvas(FigureCanvasQTAgg):
    """A matplotlib canvas displaying a graph.

    Positions are expected in the unit square (0..1); the canvas maps
    them to its axes without knowing about pixels. The canvas does not
    own the graph or its positions.

    Hover tooltips appear when the cursor rests over a node or edge.
    Right-click invokes the context callback with both data
    coordinates and screen coordinates so the caller can place a
    menu. Selection supports nodes and, separately, at most one edge.

    Args:
        parent: Optional Qt parent widget.
        on_click: Optional callback invoked on left button press.
        on_context_menu: Optional callback invoked on right button
            press.
        on_selection_complete: Optional callback invoked when a
            rubber-band selection finishes.
        on_drag_move: Optional callback invoked on mouse motion while
            the left button is held down.
        on_drag_end: Optional callback invoked on left button release.
        dark: Whether to start with the dark theme.
    """

    def __init__(
        self,
        parent: object | None = None,
        on_click: ClickCallback | None = None,
        on_context_menu: ContextCallback | None = None,
        on_selection_complete: SelectionCallback | None = None,
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
        self._bundle_parallel = False
        self._arrow_at_middle = False

        self._bg_color = DARK_BG if dark else LIGHT_BG
        self._node_border_color = DARK_NODE_BORDER if dark else LIGHT_NODE_BORDER
        self._edge_color = DARK_EDGE if dark else LIGHT_EDGE
        self._node_label_color = DARK_NODE_LABEL if dark else LIGHT_NODE_LABEL
        self._weight_text_color = DARK_WEIGHT_TEXT if dark else LIGHT_WEIGHT_TEXT
        self._weight_bg_color = DARK_WEIGHT_BG if dark else LIGHT_WEIGHT_BG

        self._configure_axes()

        self._on_click = on_click
        self._on_context_menu = on_context_menu
        self._on_selection_complete = on_selection_complete
        self._on_drag_move = on_drag_move
        self._on_drag_end = on_drag_end

        self._last_graph: Graph | None = None
        self._last_positions: dict[int, Position] = {}
        self._last_highlighted_nodes: frozenset[int] = frozenset()
        self._last_current_node: int | None = None
        self._last_current_edge: tuple[int, int] | None = None
        self._last_highlighted_edges: frozenset[tuple[int, int]] = frozenset()
        self._last_labels: dict[int, str] = {}
        self._last_edge_labels: dict[tuple[int, int], str] = {}
        self._last_selected_nodes: frozenset[int] = frozenset()
        self._last_selected_edge: tuple[int, int] | None = None

        self._colors_start: dict[int, str] = {}
        self._colors_target: dict[int, str] = {}
        self._colors_displayed: dict[int, str] = {}
        self._transition_progress = 1.0

        self._transition_timer = QTimer(self)
        self._transition_timer.setInterval(TRANSITION_FRAME_MS)
        self._transition_timer.timeout.connect(self._on_transition_tick)

        self._pressed_node: int | None = None
        self._selection_start: tuple[float, float] | None = None
        self._selection_current: tuple[float, float] | None = None
        self._selection_additive = False
        self._selecting = False

        self._hover_target: tuple[int | None, tuple[int, int] | None] | None = None

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

    def set_bundle_parallel(self, bundle: bool) -> None:
        """Enable or disable bundling of parallel edges.

        Args:
            bundle: True to draw parallel edges as one thick line.
        """
        if bundle == self._bundle_parallel:
            return
        self._bundle_parallel = bundle
        self._redraw()

    def set_arrow_at_middle(self, middle: bool) -> None:
        """Place arrow heads of directed edges at the midpoint.

        Args:
            middle: True to draw arrows at the middle.
        """
        if middle == self._arrow_at_middle:
            return
        self._arrow_at_middle = middle
        self._redraw()

    def save_figure(
        self,
        path: Path,
        dpi: int = DEFAULT_EXPORT_DPI,
    ) -> None:
        """Save the current rendering to an image file.

        Args:
            path: Destination file path.
            dpi: Resolution for raster formats.

        Raises:
            OSError: If the file cannot be written.
            ValueError: If the file extension is not a known format.
        """
        self._figure.savefig(str(path), dpi=dpi)

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
        edge_labels: dict[tuple[int, int], str] | None = None,
        selected_nodes: frozenset[int] = frozenset(),
        selected_edge: tuple[int, int] | None = None,
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
            current_edge: Optional edge being considered.
            edge_labels: Optional per-edge text labels.
            selected_nodes: Ids of nodes to draw as selected.
            selected_edge: Optional edge to draw as selected.
        """
        self._last_graph = graph
        self._last_positions = dict(positions)
        self._last_highlighted_nodes = highlighted_nodes
        self._last_current_node = current_node
        self._last_current_edge = current_edge
        self._last_highlighted_edges = highlighted_edges
        self._last_labels = dict(labels or {})
        self._last_edge_labels = dict(edge_labels or {})
        self._last_selected_nodes = selected_nodes
        self._last_selected_edge = selected_edge

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
            self._last_selected_edge,
        )
        self._draw_nodes(
            self._last_graph,
            self._last_positions,
            self._last_highlighted_nodes,
            self._last_current_node,
            self._last_labels,
            self._colors_displayed,
            self._last_selected_nodes,
        )
        self._draw_selection_rectangle()
        self.draw()

    def _draw_selection_rectangle(self) -> None:
        if not self._selecting:
            return
        if self._selection_start is None or self._selection_current is None:
            return
        x1, y1 = self._selection_start
        x2, y2 = self._selection_current
        rect = Rectangle(
            (min(x1, x2), min(y1, y2)),
            abs(x2 - x1),
            abs(y2 - y1),
            linewidth=1.0,
            edgecolor=SELECTION_FILL,
            facecolor=SELECTION_FILL,
            alpha=SELECTION_ALPHA,
            zorder=10,
        )
        self._axes.add_patch(rect)

    def _draw_edges(
        self,
        graph: Graph,
        positions: dict[int, Position],
        highlighted: frozenset[tuple[int, int]],
        current_edge: tuple[int, int] | None,
        selected_edge: tuple[int, int] | None,
    ) -> None:
        self_loops: dict[int, list[Edge]] = {}
        normal_edges: list[Edge] = []
        for edge in graph.edges():
            if edge.source == edge.target:
                self_loops.setdefault(edge.source, []).append(edge)
            else:
                normal_edges.append(edge)

        for node_id, loops in self_loops.items():
            if node_id not in positions:
                continue
            for index, edge in enumerate(loops):
                color, width, linestyle = self._edge_style(
                    edge, highlighted, current_edge, selected_edge
                )
                self._draw_self_loop(
                    node_id,
                    edge,
                    positions,
                    color,
                    width,
                    linestyle,
                    index,
                    len(loops),
                )

        groups = _group_edges_by_endpoints(normal_edges)
        for key, edges in groups.items():
            if self._bundle_parallel and len(edges) > 1:
                self._draw_bundle(
                    key,
                    edges,
                    positions,
                    highlighted,
                    current_edge,
                    selected_edge,
                )
                continue
            total = len(edges)
            for index, edge in enumerate(edges):
                if edge.source not in positions or edge.target not in positions:
                    continue
                start = positions[edge.source]
                end = positions[edge.target]
                color, width, linestyle = self._edge_style(
                    edge, highlighted, current_edge, selected_edge
                )
                rad = _effective_rad(edge, key, _arc_rad_for_index(index, total))
                self._draw_single_edge(edge, start, end, color, width, rad, linestyle)

    def _edge_style(
        self,
        edge: Edge,
        highlighted: frozenset[tuple[int, int]],
        current_edge: tuple[int, int] | None,
        selected_edge: tuple[int, int] | None,
    ) -> tuple[str, float, str]:
        is_current = current_edge is not None and (
            (edge.source, edge.target) == current_edge
            or (edge.target, edge.source) == current_edge
        )
        if is_current:
            return COLOR_HIGHLIGHTED, 2.5, "--"
        is_selected = (
            selected_edge is not None and (edge.source, edge.target) == selected_edge
        )
        if is_selected:
            return COLOR_SELECTED, 3.5, "-"
        is_highlighted = (edge.source, edge.target) in highlighted or (
            edge.target,
            edge.source,
        ) in highlighted
        if is_highlighted:
            return COLOR_CURRENT, 2.5, "-"
        return self._edge_color, 1.0, "-"

    def _draw_single_edge(
        self,
        edge: Edge,
        start: Position,
        end: Position,
        color: str,
        width: float,
        rad: float,
        linestyle: str,
    ) -> None:
        if edge.directed and not self._arrow_at_middle:
            shortened_end = _shorten_towards(start, end, NODE_VISUAL_RADIUS)
            arrow = FancyArrowPatch(
                (start.x, start.y),
                (shortened_end.x, shortened_end.y),
                arrowstyle="->",
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
        else:
            self._draw_line(start, end, color, width, rad, linestyle)
            if edge.directed and self._arrow_at_middle:
                self._draw_middle_arrow(start, end, color, rad)
        self._draw_edge_weight(edge, start, end, rad)

    def _draw_line(
        self,
        start: Position,
        end: Position,
        color: str,
        width: float,
        rad: float,
        linestyle: str,
    ) -> None:
        if rad == 0.0:
            self._axes.plot(
                [start.x, end.x],
                [start.y, end.y],
                color=color,
                linewidth=width,
                linestyle=linestyle,
                zorder=1,
            )
            return
        arrow = FancyArrowPatch(
            (start.x, start.y),
            (end.x, end.y),
            arrowstyle="-",
            connectionstyle=f"arc3,rad={rad}",
            color=color,
            linewidth=width,
            linestyle=linestyle,
            shrinkA=0.0,
            shrinkB=0.0,
            zorder=1,
        )
        self._axes.add_patch(arrow)

    def _draw_middle_arrow(
        self,
        start: Position,
        end: Position,
        color: str,
        rad: float,
    ) -> None:
        mid_x, mid_y = _arc_midpoint(start, end, rad)
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.hypot(dx, dy)
        if length == 0.0:
            return
        ux = dx / length
        uy = dy / length
        tail = (
            mid_x - ARROW_MIDDLE_SEGMENT * ux,
            mid_y - ARROW_MIDDLE_SEGMENT * uy,
        )
        head = (
            mid_x + ARROW_MIDDLE_SEGMENT * ux,
            mid_y + ARROW_MIDDLE_SEGMENT * uy,
        )
        arrow = FancyArrowPatch(
            tail,
            head,
            arrowstyle="-|>",
            mutation_scale=ARROW_MUTATION_SCALE,
            color=color,
            linewidth=1.0,
            shrinkA=0.0,
            shrinkB=0.0,
            zorder=1.5,
        )
        self._axes.add_patch(arrow)

    def _draw_self_loop(
        self,
        node_id: int,
        edge: Edge,
        positions: dict[int, Position],
        color: str,
        width: float,
        linestyle: str,
        index: int,
        total: int,
    ) -> None:
        position = positions[node_id]
        radius = SELF_LOOP_BASE_RADIUS + SELF_LOOP_STACK_STEP * index
        offset_y = SELF_LOOP_BASE_OFFSET + SELF_LOOP_STACK_OFFSET * index
        center_x = position.x
        center_y = position.y + offset_y
        circle = Circle(
            (center_x, center_y),
            radius,
            edgecolor=color,
            facecolor="none",
            linewidth=width,
            linestyle=linestyle,
            zorder=1,
        )
        self._axes.add_patch(circle)
        label_x = center_x + radius + SELF_LOOP_LABEL_MARGIN
        self._axes.text(
            label_x,
            center_y,
            f"{edge.weight:g}",
            ha="left",
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

    def _draw_bundle(
        self,
        key: tuple[int, int],
        edges: list[Edge],
        positions: dict[int, Position],
        highlighted: frozenset[tuple[int, int]],
        current_edge: tuple[int, int] | None,
        selected_edge: tuple[int, int] | None,
    ) -> None:
        source, target = key
        if source not in positions or target not in positions:
            return
        start = positions[source]
        end = positions[target]

        any_current = current_edge is not None and any(
            (e.source, e.target) == current_edge or (e.target, e.source) == current_edge
            for e in edges
        )
        any_selected = selected_edge is not None and any(
            (e.source, e.target) == selected_edge for e in edges
        )
        any_highlighted = any(
            (e.source, e.target) in highlighted or (e.target, e.source) in highlighted
            for e in edges
        )
        if any_current:
            color = COLOR_HIGHLIGHTED
            linestyle = "--"
        elif any_selected:
            color = COLOR_SELECTED
            linestyle = "-"
        elif any_highlighted:
            color = COLOR_CURRENT
            linestyle = "-"
        else:
            color = self._edge_color
            linestyle = "-"

        count = len(edges)
        width = min(
            BUNDLE_MIN_WIDTH + BUNDLE_WIDTH_PER_EDGE * (count - 1),
            BUNDLE_MAX_WIDTH,
        )
        self._axes.plot(
            [start.x, end.x],
            [start.y, end.y],
            color=color,
            linewidth=width,
            linestyle=linestyle,
            zorder=1,
        )

        weights = sorted(e.weight for e in edges)
        weight_text = ", ".join(f"{w:g}" for w in weights)
        label = f"\u00d7{count} ({weight_text})"
        mid_x = (start.x + end.x) / 2.0
        mid_y = (start.y + end.y) / 2.0
        self._axes.text(
            mid_x,
            mid_y,
            label,
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

    def _draw_edge_weight(
        self,
        edge: Edge,
        start: Position,
        end: Position,
        rad: float,
    ) -> None:
        label = self._last_edge_labels.get(
            (edge.source, edge.target),
            self._last_edge_labels.get(
                (edge.target, edge.source),
                f"{edge.weight:g}",
            ),
        )
        mid_x, mid_y = _arc_midpoint(start, end, rad)
        self._axes.text(
            mid_x,
            mid_y,
            label,
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
        selected: frozenset[int],
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
            is_selected = node.id in selected
            if is_selected:
                border_color = COLOR_SELECTED
                border_width = SELECTED_BORDER_WIDTH
            elif is_current:
                border_color = COLOR_CURRENT
                border_width = CURRENT_BORDER_WIDTH
            else:
                border_color = self._node_border_color
                border_width = 1.0
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
            if node.label:
                self._axes.text(
                    position.x,
                    position.y - 0.07,
                    node.label,
                    ha="center",
                    va="top",
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
        """Handle a mouse press.

        Args:
            event: A matplotlib mouse event.
        """
        if event.xdata is None or event.ydata is None:
            return
        if event.button == 3:
            self._handle_context_press(event)
            return
        if event.button != 1:
            return
        x = float(event.xdata)
        y = float(event.ydata)
        node_id = self._find_node_at(x, y)
        edge = None if node_id is not None else self._find_edge_at(x, y)
        shift = "shift" in (event.key or "")
        double = bool(event.dblclick)

        self._pressed_node = node_id
        if node_id is None:
            self._selection_start = (x, y)
            self._selection_current = (x, y)
            self._selection_additive = shift
            self._selecting = False
        else:
            self._selection_start = None
            self._selection_current = None
            self._selection_additive = False
            self._selecting = False

        if self._on_click is not None:
            self._on_click(
                ClickEvent(
                    x=x,
                    y=y,
                    node_id=node_id,
                    edge=edge,
                    shift=shift,
                    double=double,
                )
            )

    def _handle_context_press(self, event: Any) -> None:
        x = float(event.xdata)
        y = float(event.ydata)
        node_id = self._find_node_at(x, y)
        edge = None if node_id is not None else self._find_edge_at(x, y)
        global_pos = self.mapToGlobal(QPoint(int(event.x), int(event.y)))
        if self._on_context_menu is not None:
            self._on_context_menu(
                ContextEvent(
                    x=x,
                    y=y,
                    node_id=node_id,
                    edge=edge,
                    global_x=global_pos.x(),
                    global_y=global_pos.y(),
                )
            )

    def _handle_motion(self, event: Any) -> None:
        """Handle mouse motion.

        Args:
            event: A matplotlib mouse event.
        """
        if event.xdata is None or event.ydata is None:
            return
        x = float(event.xdata)
        y = float(event.ydata)

        if event.button == 1 and self._pressed_node is not None:
            if self._on_drag_move is not None:
                self._on_drag_move(x, y)
            return

        if event.button == 1 and self._selection_start is not None:
            self._selection_current = (x, y)
            self._selecting = True
            self._redraw()
            return

        if event.button is None:
            self._handle_hover(event, x, y)

    def _handle_hover(self, event: Any, x: float, y: float) -> None:
        node_id = self._find_node_at(x, y)
        edge = None if node_id is not None else self._find_edge_at(x, y)
        target = (node_id, edge)
        if target == self._hover_target:
            return
        self._hover_target = target
        text = self._build_tooltip(node_id, edge)
        if text is None:
            QToolTip.hideText()
            return
        global_pos = self.mapToGlobal(QPoint(int(event.x), int(event.y)))
        QToolTip.showText(global_pos, text, self)

    def _build_tooltip(
        self,
        node_id: int | None,
        edge: tuple[int, int] | None,
    ) -> str | None:
        if self._last_graph is None:
            return None
        if node_id is not None:
            if not self._last_graph.has_node(node_id):
                return None
            node = self._last_graph.node(node_id)
            degree = len(self._last_graph.neighbors(node_id))
            lines = [f"Node {node_id}"]
            if node.label:
                lines.append(f"Label: {node.label}")
            lines.append(f"Degree: {degree}")
            return "\n".join(lines)
        if edge is not None:
            source, target = edge
            for candidate in self._last_graph.edges():
                if candidate.source == source and candidate.target == target:
                    arrow = "\u2192" if candidate.directed else "\u2014"
                    return (
                        f"Edge {source} {arrow} {target}\nWeight: {candidate.weight:g}"
                    )
            return None
        return None

    def _handle_release(self, event: Any) -> None:
        """Handle the release of the left mouse button.

        Args:
            event: A matplotlib mouse event.
        """
        if event.button != 1:
            return
        was_selecting = self._selecting
        start = self._selection_start
        current = self._selection_current
        additive = self._selection_additive

        self._pressed_node = None
        self._selection_start = None
        self._selection_current = None
        self._selecting = False
        self._selection_additive = False

        if (
            was_selecting
            and start is not None
            and current is not None
            and self._on_selection_complete is not None
        ):
            self._on_selection_complete(
                SelectionEvent(
                    x1=min(start[0], current[0]),
                    y1=min(start[1], current[1]),
                    x2=max(start[0], current[0]),
                    y2=max(start[1], current[1]),
                    additive=additive,
                )
            )
        elif self._on_drag_end is not None:
            self._on_drag_end()

    def _find_node_at(self, x: float, y: float) -> int | None:
        """Return the id of the node closest to the given point.

        Args:
            x: Horizontal coordinate of the point.
            y: Vertical coordinate of the point.

        Returns:
            The id of the closest node within NODE_HIT_RADIUS, or None.
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

        Args:
            x: Horizontal coordinate of the point.
            y: Vertical coordinate of the point.

        Returns:
            The (source, target) pair of the closest edge, or None.
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

    Self-loops are not expected here; the caller filters them out.

    Args:
        edges: The edges to group.

    Returns:
        A mapping from the sorted endpoint pair to the list of edges.
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
        rad: The curvature for the edge's slot.

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
        start: Hex color string.
        end: Hex color string of the same format.
        t: Interpolation parameter in [0.0, 1.0].

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
        A new position between start and end.
    """
    total = math.hypot(end.x - start.x, end.y - start.y)
    if total <= distance:
        return start
    ratio = (total - distance) / total
    return Position(
        x=start.x + (end.x - start.x) * ratio,
        y=start.y + (end.y - start.y) * ratio,
    )
