"""Modal dialog for entering or editing an edge weight."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

WEIGHT_MIN = -1_000_000_000.0
WEIGHT_MAX = 1_000_000_000.0
WEIGHT_DECIMALS = 2
WEIGHT_STEP = 0.1
DEFAULT_WEIGHT = 1.0


class EdgeWeightDialog(QDialog):
    """Dialog for choosing a numeric edge weight.

    The dialog is modal and returns either the chosen weight or None
    if the user cancelled. It does not touch the graph — the caller
    decides what to do with the result.

    Args:
        initial: Weight shown when the dialog opens.
        parent: Optional Qt parent widget.
    """

    def __init__(
        self,
        initial: float = DEFAULT_WEIGHT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edge weight")
        self._spin = QDoubleSpinBox(self)
        self._spin.setRange(WEIGHT_MIN, WEIGHT_MAX)
        self._spin.setDecimals(WEIGHT_DECIMALS)
        self._spin.setSingleStep(WEIGHT_STEP)
        self._spin.setValue(initial)

        form = QFormLayout()
        form.addRow("Weight:", self._spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def weight(self) -> float:
        """Return the weight currently entered in the dialog.

        Returns:
            The numeric weight.
        """
        return self._spin.value()

    @staticmethod
    def get_weight(
        initial: float = DEFAULT_WEIGHT,
        parent: QWidget | None = None,
    ) -> float | None:
        """Show the dialog and return the chosen weight.

        Args:
            initial: Weight shown when the dialog opens.
            parent: Optional Qt parent widget.

        Returns:
            The chosen weight, or None if the user cancelled.
        """
        dialog = EdgeWeightDialog(initial, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.weight()
        return None
