"""Tests for the Position value object."""

from domain.value_objects.position import Position


def test_create_position() -> None:
    """Position stores both coordinates."""
    position = Position(x=1.5, y=-2.0)
    assert position.x == 1.5
    assert position.y == -2.0


def test_positions_with_same_coordinates_are_equal() -> None:
    """Two positions with the same coordinates compare as equal."""
    assert Position(x=1.0, y=2.0) == Position(x=1.0, y=2.0)


def test_positions_with_different_coordinates_are_not_equal() -> None:
    """Positions with different coordinates compare as not equal."""
    assert Position(x=1.0, y=2.0) != Position(x=1.0, y=3.0)


def test_translate_returns_new_position() -> None:
    """translate returns a new position shifted by the given offsets."""
    original = Position(x=1.0, y=1.0)
    shifted = original.translate(dx=2.0, dy=-3.0)
    assert shifted == Position(x=3.0, y=-2.0)


def test_translate_does_not_modify_original() -> None:
    """translate leaves the original position unchanged."""
    original = Position(x=1.0, y=1.0)
    original.translate(dx=5.0, dy=5.0)
    assert original == Position(x=1.0, y=1.0)


def test_distance_to_self_is_zero() -> None:
    """The distance from a position to itself is zero."""
    position = Position(x=3.0, y=4.0)
    assert position.distance_to(position) == 0.0


def test_distance_to_is_symmetric() -> None:
    """Distance between two positions is symmetric."""
    a = Position(x=0.0, y=0.0)
    b = Position(x=3.0, y=4.0)
    assert a.distance_to(b) == b.distance_to(a)


def test_distance_to_uses_euclidean_metric() -> None:
    """Distance follows the Euclidean formula."""
    a = Position(x=0.0, y=0.0)
    b = Position(x=3.0, y=4.0)
    assert a.distance_to(b) == 5.0
