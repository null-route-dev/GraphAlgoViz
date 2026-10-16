"""Dock panel showing and editing properties of the current selection."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

WEIGHT_MIN = -1_000_000_000.0
WEIGHT_MAX = 1_000_000_000.0
WEIGHT_DECIMALS = 2


class InspectorPanel(QWidget):
    """Shows the current selection and lets the user edit it.

    The panel displays one of four states: nothing selected, a single
    node selected, a single edge selected, or multiple nodes selected.
    In the first two cases the fields are editable; in the other two
    the panel is read-only.

    Edits are reported through signals rather than applied directly:
    the panel does not know about use cases or the repository. The
    caller decides what to do with each change.

    Signals:
        node_label_changed: Emitted with (node_id, new_label) when the
            user finishes editing a node's label.
        edge_weight_changed: Emitted with (source, target, new_weight)
            when the user finishes editing an edge's weight.
        edge_directed_changed: Emitted with (source, target, directed)
            when the user toggles the directed flag of an edge.
    """

    node_label_changed = Signal(int, str)
    edge_weight_changed = Signal(int, int, float)
    edge_directed_changed = Signal(int, int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._node_id: int | None = None
        self._edge: tuple[int, int] | None = None

        self._header = QLabel("No selection", self)
        self._header.setWordWrap(True)

        self._node_id_label = QLabel("", self)
        self._node_label_edit = QLineEdit(self)
        self._node_degree_label = QLabel("", self)

        self._edge_endpoints_label = QLabel("", self)
        self._edge_weight_spin = QDoubleSpinBox(self)
        self._edge_weight_spin.setRange(WEIGHT_MIN, WEIGHT_MAX)
        self._edge_weight_spin.setDecimals(WEIGHT_DECIMALS)
        self._edge_directed_check = QCheckBox("Directed", self)

        self._form = QFormLayout()

        layout = QVBoxLayout(self)
        layout.addWidget(self._header)
        layout.addLayout(self._form)
        layout.addStretch(1)

        self._node_label_edit.editingFinished.connect(self._on_node_label_finished)
        self._edge_weight_spin.editingFinished.connect(self._on_edge_weight_finished)
        self._edge_directed_check.toggled.connect(self._on_edge_directed_toggled)

        self.show_nothing()

    def show_nothing(self) -> None:
        """Reset the panel to the empty state."""
        self._node_id = None
        self._edge = None
        self._clear_form()
        self._header.setText("No selection")

    def show_node(self, node_id: int, label: str, degree: int) -> None:
        """Show details of a single node.

        Args:
            node_id: Identifier of the node.
            label: Current label.
            degree: Number of adjacent nodes.
        """
        self._node_id = node_id
        self._edge = None
        self._clear_form()
        self._header.setText(f"Node {node_id}")
        self._node_id_label.setText(str(node_id))
        self._node_degree_label.setText(str(degree))
        self._edge_weight_spin.blockSignals(True)
        self._edge_directed_check.blockSignals(True)
        self._node_label_edit.blockSignals(True)
        self._node_label_edit.setText(label)
        self._node_label_edit.blockSignals(False)
        self._edge_weight_spin.blockSignals(False)
        self._edge_directed_check.blockSignals(False)
        self._form.addRow("Id:", self._node_id_label)
        self._form.addRow("Label:", self._node_label_edit)
        self._form.addRow("Degree:", self._node_degree_label)

    def show_edge(
        self,
        source: int,
        target: int,
        weight: float,
        directed: bool,
    ) -> None:
        """Show details of a single edge.

        Args:
            source: Source node id.
            target: Target node id.
            weight: Current weight.
            directed: Whether the edge is directed.
        """
        self._node_id = None
        self._edge = (source, target)
        self._clear_form()
        arrow = "\u2192" if directed else "\u2014"
        self._header.setText(f"Edge {source} {arrow} {target}")
        self._edge_endpoints_label.setText(f"{source} \u2192 {target}")
        self._edge_weight_spin.blockSignals(True)
        self._edge_weight_spin.setValue(weight)
        self._edge_weight_spin.blockSignals(False)
        self._edge_directed_check.blockSignals(True)
        self._edge_directed_check.setChecked(directed)
        self._edge_directed_check.blockSignals(False)
        self._form.addRow("Endpoints:", self._edge_endpoints_label)
        self._form.addRow("Weight:", self._edge_weight_spin)
        self._form.addRow("", self._edge_directed_check)

    def show_multi(self, count: int) -> None:
        """Show a summary for a multi-node selection.

        Args:
            count: Number of selected nodes.
        """
        self._node_id = None
        self._edge = None
        self._clear_form()
        self._header.setText(f"{count} nodes selected")

    def _clear_form(self) -> None:
        while self._form.rowCount() > 0:
            self._form.removeRow(0)

    def _on_node_label_finished(self) -> None:
        if self._node_id is None:
            return
        self.node_label_changed.emit(self._node_id, self._node_label_edit.text())

    def _on_edge_weight_finished(self) -> None:
        if self._edge is None:
            return
        source, target = self._edge
        self.edge_weight_changed.emit(source, target, self._edge_weight_spin.value())

    def _on_edge_directed_toggled(self, checked: bool) -> None:
        if self._edge is None:
            return
        source, target = self._edge
        self.edge_directed_changed.emit(source, target, checked)
