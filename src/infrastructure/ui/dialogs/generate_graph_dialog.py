"""Modal dialog for configuring a random graph generator."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from application.generators import (
    DEFAULT_EDGES_PER_NEW_NODE,
    DEFAULT_NEIGHBORS_PER_NODE,
    DEFAULT_PROBABILITY,
    DEFAULT_REWIRING_PROBABILITY,
    GeneratorKind,
    GeneratorRequest,
)

DEFAULT_NODE_COUNT = 20
MIN_NODE_COUNT = 2
MAX_NODE_COUNT = 500

_ROW_NODES = 1
_ROW_PROBABILITY = 2
_ROW_EDGES = 3
_ROW_NEIGHBORS = 4
_ROW_REWIRING = 5

_KIND_ROWS: dict[GeneratorKind, set[int]] = {
    GeneratorKind.ERDOS_RENYI: {_ROW_PROBABILITY},
    GeneratorKind.BARABASI_ALBERT: {_ROW_EDGES},
    GeneratorKind.WATTS_STROGATZ: {_ROW_NEIGHBORS, _ROW_REWIRING},
}


class GenerateGraphDialog(QDialog):
    """Dialog for choosing a random graph generator and its parameters.

    The dialog shows a shared node-count field and one or more
    parameter fields specific to the selected generator. Switching
    the generator reveals the relevant rows and hides the others
    through ``setRowVisible``, so widgets are never recreated and the
    selection is preserved.

    The dialog is modal and returns either a fully configured
    GeneratorRequest or None if the user cancelled.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate graph")
        self._kind_combo = QComboBox(self)
        self._kind_combo.addItem(
            "Erd\u0151s\u2013R\u00e9nyi", GeneratorKind.ERDOS_RENYI
        )
        self._kind_combo.addItem(
            "Barab\u00e1si\u2013Albert", GeneratorKind.BARABASI_ALBERT
        )
        self._kind_combo.addItem("Watts\u2013Strogatz", GeneratorKind.WATTS_STROGATZ)

        self._node_count_spin = QSpinBox(self)
        self._node_count_spin.setRange(MIN_NODE_COUNT, MAX_NODE_COUNT)
        self._node_count_spin.setValue(DEFAULT_NODE_COUNT)

        self._probability_spin = QDoubleSpinBox(self)
        self._probability_spin.setRange(0.0, 1.0)
        self._probability_spin.setDecimals(2)
        self._probability_spin.setSingleStep(0.05)
        self._probability_spin.setValue(DEFAULT_PROBABILITY)

        self._edges_spin = QSpinBox(self)
        self._edges_spin.setRange(1, MAX_NODE_COUNT - 1)
        self._edges_spin.setValue(DEFAULT_EDGES_PER_NEW_NODE)

        self._neighbors_spin = QSpinBox(self)
        self._neighbors_spin.setRange(2, MAX_NODE_COUNT - 1)
        self._neighbors_spin.setSingleStep(2)
        self._neighbors_spin.setValue(DEFAULT_NEIGHBORS_PER_NODE)

        self._rewiring_spin = QDoubleSpinBox(self)
        self._rewiring_spin.setRange(0.0, 1.0)
        self._rewiring_spin.setDecimals(2)
        self._rewiring_spin.setSingleStep(0.05)
        self._rewiring_spin.setValue(DEFAULT_REWIRING_PROBABILITY)

        self._form = QFormLayout()
        self._form.addRow("Generator:", self._kind_combo)
        self._form.addRow("Nodes:", self._node_count_spin)
        self._form.addRow("Probability:", self._probability_spin)
        self._form.addRow("Edges per new node:", self._edges_spin)
        self._form.addRow("Neighbors per node:", self._neighbors_spin)
        self._form.addRow("Rewiring probability:", self._rewiring_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(buttons)

        self._kind_combo.currentIndexChanged.connect(self._update_visible_rows)
        self._update_visible_rows()

    def _update_visible_rows(self) -> None:
        kind = self._kind_combo.currentData()
        visible: set[int] = set()
        if isinstance(kind, GeneratorKind):
            visible = _KIND_ROWS.get(kind, set())
        for index in range(self._form.rowCount()):
            if index == _ROW_NODES:
                self._form.setRowVisible(index, True)
            elif index >= _ROW_PROBABILITY:
                self._form.setRowVisible(index, index in visible)

    def request(self) -> GeneratorRequest:
        """Return a request built from the current field values.

        Returns:
            A GeneratorRequest ready to be passed to ``generate``.
        """
        kind = self._kind_combo.currentData()
        if not isinstance(kind, GeneratorKind):
            kind = GeneratorKind.ERDOS_RENYI
        return GeneratorRequest(
            kind=kind,
            node_count=self._node_count_spin.value(),
            probability=self._probability_spin.value(),
            edges_per_new_node=self._edges_spin.value(),
            neighbors_per_node=self._neighbors_spin.value(),
            rewiring_probability=self._rewiring_spin.value(),
        )

    @staticmethod
    def get_request(parent: QWidget | None = None) -> GeneratorRequest | None:
        """Show the dialog and return the chosen request.

        Args:
            parent: Optional parent widget.

        Returns:
            The configured request, or None if cancelled.
        """
        dialog = GenerateGraphDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.request()
        return None
