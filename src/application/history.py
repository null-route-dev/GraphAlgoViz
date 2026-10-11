"""Undo/redo history via full-state snapshots."""

import copy
from dataclasses import dataclass

from domain.entities.graph import Graph
from domain.value_objects.position import Position


@dataclass(frozen=True)
class GraphState:
    """Immutable snapshot of a graph and its node positions.

    A snapshot captures everything the editor treats as the user's
    work: the graph itself and the positions of its nodes. Snapshots
    are always deep copies, so the live graph can be mutated freely
    without affecting history.

    Args:
        graph: A deep copy of the graph at the moment of the
            snapshot.
        positions: A copy of the node positions at the same moment.
    """

    graph: Graph
    positions: dict[int, Position]


def snapshot(graph: Graph, positions: dict[int, Position]) -> GraphState:
    """Create a deep snapshot of the given graph and positions.

    Args:
        graph: The live graph to copy.
        positions: The live positions to copy.

    Returns:
        A GraphState with deep copies of both inputs.
    """
    return GraphState(
        graph=copy.deepcopy(graph),
        positions=dict(positions),
    )


class EditHistory:
    """Linear undo/redo history of graph states.

    The history is a list of GraphState snapshots with a cursor that
    points to the current state. Pushing a new state after an undo
    discards the redo tail, which is the standard behaviour in every
    editor.

    The class also tracks which state was last saved, so the caller
    can ask "is the project dirty?" and get the correct answer for
    scenarios like: edit, save, edit, undo — the project is no longer
    dirty, because the undo returned to the saved state.

    Args:
        initial: The state the history starts from. This is treated
            as the current and the saved state.
    """

    def __init__(self, initial: GraphState) -> None:
        self._states: list[GraphState] = [initial]
        self._index: int = 0
        self._saved_index: int = 0

    @property
    def current(self) -> GraphState:
        """Return the state at the current cursor position.

        Returns:
            The current GraphState.
        """
        return self._states[self._index]

    def can_undo(self) -> bool:
        """Whether an undo is possible.

        Returns:
            True if the cursor is past the first state.
        """
        return self._index > 0

    def can_redo(self) -> bool:
        """Whether a redo is possible.

        Returns:
            True if the cursor is before the last state.
        """
        return self._index < len(self._states) - 1

    def push(self, state: GraphState) -> None:
        """Append a new state and move the cursor to it.

        Any states after the current cursor position are discarded,
        because a new edit invalidates the redo tail. If the saved
        state was in that tail, it is forgotten, and the project is
        treated as always dirty from that point.

        Args:
            state: The new state to store.
        """
        if self._saved_index > self._index:
            self._saved_index = -1
        del self._states[self._index + 1 :]
        self._states.append(state)
        self._index = len(self._states) - 1

    def undo(self) -> GraphState:
        """Move the cursor back by one and return the new state.

        Returns:
            The state at the new cursor position.

        Raises:
            RuntimeError: If there is nothing to undo.
        """
        if not self.can_undo():
            raise RuntimeError("Nothing to undo")
        self._index -= 1
        return self._states[self._index]

    def redo(self) -> GraphState:
        """Move the cursor forward by one and return the new state.

        Returns:
            The state at the new cursor position.

        Raises:
            RuntimeError: If there is nothing to redo.
        """
        if not self.can_redo():
            raise RuntimeError("Nothing to redo")
        self._index += 1
        return self._states[self._index]

    def mark_saved(self) -> None:
        """Mark the current state as the saved one."""
        self._saved_index = self._index

    def is_dirty(self) -> bool:
        """Whether the current state differs from the saved state.

        Returns:
            True if there are unsaved changes.
        """
        return self._index != self._saved_index

    def reset(self, initial: GraphState) -> None:
        """Replace the entire history with a single saved state.

        Used after New, Open, and any operation that should start a
        fresh editing session.

        Args:
            initial: The new starting state, marked as saved.
        """
        self._states = [initial]
        self._index = 0
        self._saved_index = 0

    @property
    def size(self) -> int:
        """Number of states currently stored.

        Returns:
            The length of the internal state list.
        """
        return len(self._states)
