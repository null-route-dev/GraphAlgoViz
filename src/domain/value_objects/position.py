"""Position value object of the graph domain."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """A point in a two-dimensional space.

    Position is not a mathematical property of a graph. It describes where
    a node is placed on a canvas and is persisted together with the graph,
    because the user cares about the visual arrangement.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """

    x: float
    y: float

    def translate(self, dx: float, dy: float) -> "Position":
        """Return a new position shifted by the given offsets.

        Args:
            dx: Offset along the horizontal axis.
            dy: Offset along the vertical axis.

        Returns:
            A new Position shifted by (dx, dy).
        """
        return Position(self.x + dx, self.y + dy)

    def distance_to(self, other: "Position") -> float:
        """Return the Euclidean distance to another position.

        Args:
            other: The position to measure the distance to.

        Returns:
            The Euclidean distance between the two positions.
        """
        return math.hypot(self.x - other.x, self.y - other.y)
