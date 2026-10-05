"""Application settings persisted with QSettings.

QSettings stores key-value pairs in a platform-specific location:
the registry on Windows, plist files on macOS, and ini files under
``~/.config`` on Linux. This module wraps QSettings with a typed API
so that the rest of the application does not deal with raw strings
and type conversions.
"""

from PySide6.QtCore import QSettings

ORG_NAME = "GraphAlgoViz"
APP_NAME = "GraphAlgoViz"

KEY_DARK_THEME = "ui/dark_theme"
DEFAULT_DARK_THEME = True


class AppSettings:
    """Typed access to the application's persisted settings.

    Args:
        settings: Optional QSettings instance to use. When omitted, a
            QSettings for ORG_NAME and APP_NAME is created. Tests pass
            an instance backed by a temporary file to avoid touching
            the user's real settings.
    """

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(ORG_NAME, APP_NAME)

    def dark_theme(self) -> bool:
        """Return whether the dark theme is enabled.

        Returns:
            True if the dark theme was selected on the previous run,
            or the default value if no preference was saved.
        """
        value = self._settings.value(KEY_DARK_THEME, DEFAULT_DARK_THEME)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def set_dark_theme(self, dark: bool) -> None:
        """Persist the dark theme preference.

        Args:
            dark: True for the dark theme, False for the light one.
        """
        self._settings.setValue(KEY_DARK_THEME, dark)
        self._settings.sync()
