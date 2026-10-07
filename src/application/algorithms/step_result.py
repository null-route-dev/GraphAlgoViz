"""Result of a single algorithm step."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepResult:
    """The outcome of a single algorithm step.

    Every algorithm produces one of these per step. The UI layer reads
    them and decides how to render the current state: which nodes to
    highlight, what edges to emphasize, what to show in the status bar,
    and — for algorithms that compute a matrix — which cells of that
    matrix to display.

    The result is a snapshot. It does not reference mutable algorithm
    state, so the UI can safely hold onto it for animation or history.

    Args:
        visited: Ids of nodes fully processed so far.
        current: Id of the node being processed in this step, if any.
        current_edge: Endpoints of the edge being considered in this
            step, if any. Used by algorithms that process edges one at
            a time, such as Kruskal's.
        frontier: Ids waiting to be processed (stack or queue order).
        tree_edges: Edges forming the traversal tree.
        labels: Optional per-node text labels (for example, distances).
        node_colors: Optional per-node fill colors as hex strings.
        matrix: Optional matrix of values indexed by (row, col) node
            ids. Used by algorithms that produce a table rather than
            a single per-node value.
        highlight_cell: Optional (row, col) node id pair identifying
            the matrix cell to emphasize in this step.
        info: Human-readable description of this step.
    """

    visited: frozenset[int] = frozenset()
    current: int | None = None
    current_edge: tuple[int, int] | None = None
    frontier: tuple[int, ...] = ()
    tree_edges: frozenset[tuple[int, int]] = frozenset()
    labels: dict[int, str] = field(default_factory=dict)
    node_colors: dict[int, str] = field(default_factory=dict)
    matrix: dict[tuple[int, int], str] = field(default_factory=dict)
    highlight_cell: tuple[int, int] | None = None
    info: str = ""
