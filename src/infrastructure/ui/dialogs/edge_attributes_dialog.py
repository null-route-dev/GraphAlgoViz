"""Modal dialog for entering or editing edge attributes."""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
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
DEFAULT_DIRECTED = False


@dataclass(frozen=True)
class EdgeAttributes:
    """User-selected attributes for an edge.

    Args:
        weight: Numeric weight of the edge.
        directed: Whether the edge has a direction.
    """

    weight: float
    directed: bool


class EdgeAttributesDialog(QDialog):
    """Dialog for choosing edge weight and direction.

    The dialog is modal and returns either the chosen attributes or
    None if the user cancelled. It does not touch the graph — the
    caller decides what to do with the result.

    Args:
        initial_weight: Weight shown when the dialog opens.
        initial_directed: State of the directed checkbox when the
            dialog opens.
        parent: Optional Qt parent widget.
    """

    def __init__(
        self,
        initial_weight: float = DEFAULT_WEIGHT,
        initial_directed: bool = DEFAULT_DIRECTED,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edge attributes")
        self._weight_spin = QDoubleSpinBox(self)
        self._weight_spin.setRange(WEIGHT_MIN, WEIGHT_MAX)
        self._weight_spin.setDecimals(WEIGHT_DECIMALS)
        self._weight_spin.setSingleStep(WEIGHT_STEP)
        self._weight_spin.setValue(initial_weight)

        self._directed_check = QCheckBox("Directed", self)
        self._directed_check.setChecked(initial_directed)

        form = QFormLayout()
        form.addRow("Weight:", self._weight_spin)
        form.addRow("", self._directed_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def attributes(self) -> EdgeAttributes:
        """Return the attributes currently entered in the dialog.

        Returns:
            The chosen weight and direction.
        """
        return EdgeAttributes(
            weight=self._weight_spin.value(),
            directed=self._directed_check.isChecked(),
        )

    @staticmethod
    def get_attributes(
        initial_weight: float = DEFAULT_WEIGHT,
        initial_directed: bool = DEFAULT_DIRECTED,
        parent: QWidget | None = None,
    ) -> EdgeAttributes | None:
        """Show the dialog and return the chosen attributes.

        Args:
            initial_weight: Weight shown when the dialog opens.
            initial_directed: State of the directed checkbox when the
                dialog opens.
            parent: Optional Qt parent widget.

        Returns:
            The chosen attributes, or None if the user cancelled.
        """
        dialog = EdgeAttributesDialog(initial_weight, initial_directed, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.attributes()
        return None
