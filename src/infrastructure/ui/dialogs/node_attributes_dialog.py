"""Modal dialog for editing a node's label."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class NodeAttributesDialog(QDialog):
    """Dialog for choosing a node's label.

    The dialog is modal and returns either the entered label or None
    if the user cancelled. Node ids are not editable: changing an id
    would break every edge that references it.

    Args:
        initial_label: Label shown when the dialog opens.
        node_id: Identifier of the node being edited, shown as a
            read-only field for context.
        parent: Optional Qt parent widget.
    """

    def __init__(
        self,
        initial_label: str = "",
        node_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Node")
        self._label_edit = QLineEdit(initial_label, self)

        form = QFormLayout()
        if node_id is not None:
            form.addRow("Id:", _readonly_label(node_id, self))
        form.addRow("Label:", self._label_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def label(self) -> str:
        """Return the label currently entered in the dialog.

        Returns:
            The label text.
        """
        return self._label_edit.text()

    @staticmethod
    def get_label(
        initial_label: str = "",
        node_id: int | None = None,
        parent: QWidget | None = None,
    ) -> str | None:
        """Show the dialog and return the chosen label.

        Args:
            initial_label: Label shown when the dialog opens.
            node_id: Identifier of the node, for display.
            parent: Optional Qt parent widget.

        Returns:
            The chosen label, or None if the user cancelled.
        """
        dialog = NodeAttributesDialog(initial_label, node_id, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.label()
        return None


def _readonly_label(node_id: int, parent: QWidget) -> QLineEdit:
    field = QLineEdit(str(node_id), parent)
    field.setReadOnly(True)
    return field
