"""Node entity of the graph domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """A vertex in a graph.

    The id is the identity of the node and must be unique within a graph.
    The label is an optional human-readable name used for display.

    Args:
        id: Unique identifier of the node.
        label: Optional human-readable name.
    """

    id: int
    label: str = ""
