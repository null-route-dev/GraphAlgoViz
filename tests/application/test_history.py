"""Tests for the edit history."""

import pytest

from application.history import EditHistory, GraphState, snapshot
from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node
from domain.value_objects.position import Position


def build_state(num_nodes: int = 0) -> GraphState:
    """Return a fresh state with the given number of nodes."""
    graph = Graph()
    positions: dict[int, Position] = {}
    for i in range(1, num_nodes + 1):
        graph.add_node(Node(id=i))
        positions[i] = Position(x=i * 0.1, y=i * 0.1)
    return snapshot(graph, positions)


def test_snapshot_is_deep_copy_of_graph() -> None:
    """The snapshot's graph is independent of the live graph."""
    live = Graph()
    live.add_node(Node(id=1))
    state = snapshot(live, {})

    live.add_node(Node(id=2))

    assert state.graph.node_count == 1
    assert live.node_count == 2


def test_snapshot_is_copy_of_positions() -> None:
    """The snapshot's positions dict is independent of the live one."""
    positions = {1: Position(x=0.1, y=0.2)}
    state = snapshot(Graph(), positions)

    positions[1] = Position(x=0.9, y=0.9)

    assert state.positions[1] == Position(x=0.1, y=0.2)


def test_initial_history_has_one_state() -> None:
    """A new history stores exactly the initial state."""
    history = EditHistory(build_state())

    assert history.size == 1
    assert history.can_undo() is False
    assert history.can_redo() is False


def test_initial_history_is_clean() -> None:
    """A fresh history is not dirty."""
    history = EditHistory(build_state())

    assert history.is_dirty() is False


def test_push_adds_state() -> None:
    """After push, the new state becomes current."""
    history = EditHistory(build_state())
    second = build_state(num_nodes=1)
    history.push(second)

    assert history.size == 2
    assert history.current is second


def test_undo_returns_previous_state() -> None:
    """Undo returns the state before the last push."""
    first = build_state()
    history = EditHistory(first)
    history.push(build_state(num_nodes=1))

    restored = history.undo()

    assert restored is first


def test_redo_returns_next_state() -> None:
    """Redo returns the state that was undone."""
    history = EditHistory(build_state())
    second = build_state(num_nodes=1)
    history.push(second)
    history.undo()

    restored = history.redo()

    assert restored is second


def test_undo_without_history_raises() -> None:
    """Undo on the initial state raises RuntimeError."""
    history = EditHistory(build_state())

    with pytest.raises(RuntimeError, match="Nothing to undo"):
        history.undo()


def test_redo_without_history_raises() -> None:
    """Redo at the end of history raises RuntimeError."""
    history = EditHistory(build_state())

    with pytest.raises(RuntimeError, match="Nothing to redo"):
        history.redo()


def test_push_after_undo_discards_redo_tail() -> None:
    """A new edit after undo removes the abandoned future states."""
    history = EditHistory(build_state())
    history.push(build_state(num_nodes=1))
    history.push(build_state(num_nodes=2))
    history.undo()
    history.undo()
    assert history.can_redo() is True

    history.push(build_state(num_nodes=3))

    assert history.can_redo() is False
    assert history.size == 2


def test_mark_saved_makes_history_clean() -> None:
    """After mark_saved, is_dirty returns False."""
    history = EditHistory(build_state())
    history.push(build_state(num_nodes=1))
    assert history.is_dirty() is True

    history.mark_saved()

    assert history.is_dirty() is False


def test_edit_after_save_is_dirty() -> None:
    """A push after save makes the history dirty again."""
    history = EditHistory(build_state())
    history.push(build_state(num_nodes=1))
    history.mark_saved()
    history.push(build_state(num_nodes=2))

    assert history.is_dirty() is True


def test_undo_to_saved_state_is_clean() -> None:
    """Undoing back to the saved state clears the dirty flag."""
    history = EditHistory(build_state())
    history.mark_saved()
    history.push(build_state(num_nodes=1))
    assert history.is_dirty() is True

    history.undo()

    assert history.is_dirty() is False


def test_redo_away_from_saved_state_is_dirty() -> None:
    """Redoing away from the saved state makes the history dirty."""
    history = EditHistory(build_state())
    history.mark_saved()
    history.push(build_state(num_nodes=1))
    history.undo()
    assert history.is_dirty() is False

    history.redo()

    assert history.is_dirty() is True


def test_saved_state_discarded_by_push_is_dirty_forever() -> None:
    """If the saved state is discarded, the project is always dirty."""
    history = EditHistory(build_state())
    history.push(build_state(num_nodes=1))
    history.mark_saved()
    history.undo()
    history.push(build_state(num_nodes=2))

    assert history.is_dirty() is True


def test_reset_replaces_history() -> None:
    """Reset discards everything and starts clean."""
    history = EditHistory(build_state())
    history.push(build_state(num_nodes=1))
    history.push(build_state(num_nodes=2))

    fresh = build_state(num_nodes=3)
    history.reset(fresh)

    assert history.size == 1
    assert history.current is fresh
    assert history.can_undo() is False
    assert history.can_redo() is False
    assert history.is_dirty() is False


def test_round_trip_edit_undo_redo() -> None:
    """A round of edit, undo, and redo returns consistent states."""
    s0 = build_state()
    history = EditHistory(s0)
    s1 = build_state(num_nodes=1)
    s2 = build_state(num_nodes=2)
    history.push(s1)
    history.push(s2)

    assert history.undo() is s1
    assert history.undo() is s0
    assert history.redo() is s1
    assert history.redo() is s2
    assert history.can_redo() is False


def test_snapshot_preserves_edge_data() -> None:
    """Edges are copied including their weight and direction."""
    live = Graph()
    live.add_node(Node(id=1))
    live.add_node(Node(id=2))
    live.add_edge(Edge(source=1, target=2, weight=2.5, directed=True))
    state = snapshot(live, {})

    edge = state.graph.edges()[0]

    assert edge.source == 1
    assert edge.target == 2
    assert edge.weight == 2.5
    assert edge.directed is True


def test_snapshot_is_independent_for_edges() -> None:
    """Mutating edges of the live graph does not affect the snapshot."""
    live = Graph()
    live.add_node(Node(id=1))
    live.add_node(Node(id=2))
    live.add_edge(Edge(source=1, target=2))
    state = snapshot(live, {})

    live.remove_edge(1, 2)

    assert state.graph.edge_count == 1
    assert live.edge_count == 0
