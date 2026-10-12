"""Tests for the node attributes dialog."""

from infrastructure.ui.dialogs.node_attributes_dialog import (
    NodeAttributesDialog,
)


def test_dialog_starts_with_initial_label(qtbot: object) -> None:
    """The label field is prefilled with the initial label."""
    _ = qtbot
    dialog = NodeAttributesDialog(initial_label="A")
    try:
        assert dialog.label() == "A"
    finally:
        dialog.deleteLater()


def test_dialog_starts_empty_without_initial(qtbot: object) -> None:
    """Without an initial label, the field is empty."""
    _ = qtbot
    dialog = NodeAttributesDialog()
    try:
        assert dialog.label() == ""
    finally:
        dialog.deleteLater()


def test_dialog_reads_label_field(qtbot: object) -> None:
    """The label method returns the current field content."""
    _ = qtbot
    dialog = NodeAttributesDialog()
    try:
        dialog._label_edit.setText("hello")
        assert dialog.label() == "hello"
    finally:
        dialog.deleteLater()


def test_dialog_with_node_id(qtbot: object) -> None:
    """The dialog accepts a node id for display purposes."""
    _ = qtbot
    dialog = NodeAttributesDialog(initial_label="A", node_id=42)
    try:
        assert dialog.label() == "A"
    finally:
        dialog.deleteLater()
