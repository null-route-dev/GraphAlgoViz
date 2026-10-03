"""Application theme helpers."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

_original_palette: QPalette | None = None
_original_style: str = ""


def apply_theme(app: QApplication, dark: bool) -> None:
    """Apply either the dark or the original system theme.

    On the first call, the original palette and style are saved so
    that switching back to the light theme restores exactly what was
    active before this module touched anything. Subsequent calls reuse
    the saved values.

    The dark theme uses Qt's Fusion style with a hand-tuned palette.
    Fusion is chosen because it looks consistent across platforms and
    respects custom palettes more reliably than the native styles.

    Args:
        app: The application to restyle.
        dark: True to apply the dark theme, False to restore the
            original system theme.
    """
    global _original_palette, _original_style
    if _original_palette is None:
        _original_palette = app.palette()
        _original_style = app.style().objectName()

    if dark:
        app.setStyle("Fusion")
        app.setPalette(_dark_palette())
    else:
        app.setStyle(_original_style)
        app.setPalette(_original_palette)


def _dark_palette() -> QPalette:
    """Return the palette used by the dark theme.

    Returns:
        A QPalette with dark backgrounds and light text.
    """
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(127, 127, 127),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(127, 127, 127),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(127, 127, 127),
    )
    return palette
