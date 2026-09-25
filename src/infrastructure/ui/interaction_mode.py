"""Interaction modes for the graph canvas."""

from enum import Enum, auto


class InteractionMode(Enum):
    """Determines how the canvas reacts to mouse input.

    The mode is owned by the main window and read by the canvas on
    every mouse event. Switching modes does not affect the graph or
    its positions — only the interpretation of user input.
    """

    SELECT = auto()
    ADD_NODE = auto()
    ADD_EDGE = auto()
    DELETE = auto()

    @property
    def display_name(self) -> str:
        """Human-readable name shown in the status bar.

        Returns:
            A short title-cased label for the mode.
        """
        return self.name.replace("_", " ").title()
