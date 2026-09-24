"""Canvas widget that renders a graph using matplotlib."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from domain.entities.graph import Graph
from domain.value_objects.position import Position


class GraphCanvas(FigureCanvasQTAgg):
    """A matplotlib canvas displaying a graph.

    Positions are expected in the unit square (0..1); the canvas maps
    them to its axes without knowing about pixels. The canvas does not
    own the graph or its positions — it reads them on every draw.

    Args:
        parent: Optional Qt parent widget.
    """

    def __init__(self, parent: object | None = None) -> None:
        self._figure = Figure(figsize=(6, 6), tight_layout=True)
        self._axes = self._figure.add_subplot(111)
        super().__init__(self._figure)
        if parent is not None:
            self.setParent(parent)  # type: ignore[arg-type]
        self._configure_axes()

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
        highlighted_edges: frozenset[tuple[int, int]] = frozenset(),
        labels: dict[int, str] | None = None,
    ) -> None:
        """Render the graph on the canvas.

        Args:
            graph: The graph to render.
            positions: Mapping from node id to position.
            highlighted_nodes: Ids of nodes to emphasize.
            highlighted_edges: Edges to emphasize.
            labels: Optional per-node text labels.
        """
        self._axes.clear()
        self._configure_axes()
        self._draw_edges(graph, positions, highlighted_edges)
        self._draw_nodes(graph, positions, highlighted_nodes, labels or {})
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
            color = "#d62728" if is_highlighted else "#888888"
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
        labels: dict[int, str],
    ) -> None:
        for node in graph.nodes():
            if node.id not in positions:
                continue
            position = positions[node.id]
            is_highlighted = node.id in highlighted
            color = "#d62728" if is_highlighted else "#1f77b4"
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
