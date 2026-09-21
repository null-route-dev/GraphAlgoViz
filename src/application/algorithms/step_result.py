"""Result of a single algorithm step."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepResult:
    """The outcome of a single algorithm step.

    Every algorithm produces one of these per step. The UI layer reads
    them and decides how to render the current state: which nodes to
    highlight, what edges to emphasize, what to show in the status bar.

    The result is a snapshot. It does not reference mutable algorithm
    state, so the UI can safely hold onto it for animation or history.

    Args:
        visited: Ids of nodes fully processed so far.
        current: Id of the node being processed in this step, if any.
        frontier: Ids waiting to be processed (stack or queue order).
        tree_edges: Edges forming the traversal tree.
        labels: Optional per-node text labels (for example, distances).
        info: Human-readable description of this step.
    """

    visited: frozenset[int] = frozenset()
    current: int | None = None
    frontier: tuple[int, ...] = ()
    tree_edges: frozenset[tuple[int, int]] = frozenset()
    labels: dict[int, str] = field(default_factory=dict)
    info: str = ""
