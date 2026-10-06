"""Widget displaying a matrix of algorithm results."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

CELL_HIGHLIGHT_COLOR = QColor("#ffcc66")
AXIS_HIGHLIGHT_COLOR = QColor("#99ccff")


class MatrixView(QTableWidget):
    """A read-only table that displays a matrix of string values.

    Rows and columns are indexed by node ids. The widget does not own
    the data — it is called with a fresh matrix on every update and
    reflects the last call. Cell highlights show the current step of
    the algorithm: one cell is emphasized as the current (row, col)
    pair, and a row and column are emphasized for the current
    intermediate node.

    Args:
        parent: Optional Qt parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def set_matrix(
        self,
        node_ids: list[int],
        matrix: dict[tuple[int, int], str],
        highlight_cell: tuple[int, int] | None = None,
        highlight_axis: int | None = None,
    ) -> None:
        """Replace the contents of the table with a new matrix.

        Args:
            node_ids: Ordered list of node ids defining row and column
                headers.
            matrix: Mapping from (row_id, col_id) to the string to
                display in the cell.
            highlight_cell: Cell to emphasize, or None.
            highlight_axis: Node id whose row and column should be
                emphasized, or None.
        """
        self.setRowCount(len(node_ids))
        self.setColumnCount(len(node_ids))
        self.setHorizontalHeaderLabels([str(n) for n in node_ids])
        self.setVerticalHeaderLabels([str(n) for n in node_ids])
        for row, row_id in enumerate(node_ids):
            for col, col_id in enumerate(node_ids):
                text = matrix.get((row_id, col_id), "")
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row, col, item)
        self._apply_highlights(node_ids, highlight_cell, highlight_axis)

    def clear_matrix(self) -> None:
        """Reset the table to an empty state."""
        self.setRowCount(0)
        self.setColumnCount(0)

    def _apply_highlights(
        self,
        node_ids: list[int],
        highlight_cell: tuple[int, int] | None,
        highlight_axis: int | None,
    ) -> None:
        if highlight_axis is not None and highlight_axis in node_ids:
            index = node_ids.index(highlight_axis)
            for col in range(self.columnCount()):
                item = self.item(index, col)
                if item is not None:
                    item.setBackground(QBrush(AXIS_HIGHLIGHT_COLOR))
            for row in range(self.rowCount()):
                item = self.item(row, index)
                if item is not None:
                    item.setBackground(QBrush(AXIS_HIGHLIGHT_COLOR))
        if highlight_cell is not None:
            row_id, col_id = highlight_cell
            if row_id in node_ids and col_id in node_ids:
                row = node_ids.index(row_id)
                col = node_ids.index(col_id)
                item = self.item(row, col)
                if item is not None:
                    item.setBackground(QBrush(CELL_HIGHLIGHT_COLOR))
