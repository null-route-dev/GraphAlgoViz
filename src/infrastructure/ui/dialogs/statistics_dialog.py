"""Modal dialog showing graph statistics."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from application.statistics import GraphStatistics


class StatisticsDialog(QDialog):
    """Dialog showing summary statistics for a graph.

    The dialog is read-only. It displays the values computed by
    ``compute_statistics`` and offers a single Close button. Missing
    metrics (diameter and average path length on disconnected or
    large graphs) are shown as "n/a".

    Args:
        stats: The statistics to display.
        parent: Optional Qt parent widget.
    """

    def __init__(
        self,
        stats: GraphStatistics,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Graph statistics")

        self._form = QFormLayout()
        self._form.addRow("Nodes:", _make_label(str(stats.node_count), self))
        self._form.addRow("Edges:", _make_label(str(stats.edge_count), self))
        self._form.addRow("Density:", _make_label(f"{stats.density:.3f}", self))
        self._form.addRow(
            "Average degree:",
            _make_label(f"{stats.average_degree:.2f}", self),
        )
        self._form.addRow(
            "Components:",
            _make_label(str(stats.component_count), self),
        )
        self._form.addRow(
            "Diameter:",
            _make_label(_format_optional_int(stats.diameter), self),
        )
        self._form.addRow(
            "Average path length:",
            _make_label(_format_optional_float(stats.average_path_length), self),
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(buttons)

    @staticmethod
    def show_stats(
        stats: GraphStatistics,
        parent: QWidget | None = None,
    ) -> None:
        """Show the statistics dialog modally.

        Args:
            stats: The statistics to display.
            parent: Optional Qt parent widget.
        """
        dialog = StatisticsDialog(stats, parent)
        dialog.exec()


def _make_label(text: str, parent: QWidget) -> QLabel:
    """Create a read-only label with selectable text.

    Args:
        text: The text to display.
        parent: The parent widget.

    Returns:
        A QLabel with mouse-selectable text.
    """
    label = QLabel(text, parent)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def _format_optional_int(value: int | None) -> str:
    """Format an optional integer for display.

    Args:
        value: The value, or None.

    Returns:
        The integer as text, or "n/a".
    """
    return "n/a" if value is None else str(value)


def _format_optional_float(value: float | None) -> str:
    """Format an optional float for display.

    Args:
        value: The value, or None.

    Returns:
        The float with two decimals, or "n/a".
    """
    return "n/a" if value is None else f"{value:.2f}"
