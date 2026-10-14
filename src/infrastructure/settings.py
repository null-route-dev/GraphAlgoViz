"""Application settings persisted with QSettings."""

from PySide6.QtCore import QSettings

ORG_NAME = "GraphAlgoViz"
APP_NAME = "GraphAlgoViz"

KEY_DARK_THEME = "ui/dark_theme"
KEY_SNAP_TO_GRID = "ui/snap_to_grid"
KEY_BUNDLE_PARALLEL = "ui/bundle_parallel_edges"
KEY_ARROW_AT_MIDDLE = "ui/arrow_at_middle"

DEFAULT_DARK_THEME = True
DEFAULT_SNAP_TO_GRID = False
DEFAULT_BUNDLE_PARALLEL = False
DEFAULT_ARROW_AT_MIDDLE = False


class AppSettings:
    """Typed access to the application's persisted settings.

    Args:
        settings: Optional QSettings instance to use.
    """

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(ORG_NAME, APP_NAME)

    def dark_theme(self) -> bool:
        """Return whether the dark theme is enabled.

        Returns:
            True if the dark theme was selected on the previous run.
        """
        return self._read_bool(KEY_DARK_THEME, DEFAULT_DARK_THEME)

    def set_dark_theme(self, dark: bool) -> None:
        """Persist the dark theme preference.

        Args:
            dark: True for the dark theme, False for the light one.
        """
        self._write_bool(KEY_DARK_THEME, dark)

    def snap_to_grid(self) -> bool:
        """Return whether snap-to-grid is enabled.

        Returns:
            True if nodes snap to grid during drag and creation.
        """
        return self._read_bool(KEY_SNAP_TO_GRID, DEFAULT_SNAP_TO_GRID)

    def set_snap_to_grid(self, enabled: bool) -> None:
        """Persist the snap-to-grid preference.

        Args:
            enabled: True to enable snapping, False to disable.
        """
        self._write_bool(KEY_SNAP_TO_GRID, enabled)

    def bundle_parallel_edges(self) -> bool:
        """Return whether parallel edges are drawn as a single bundle.

        Returns:
            True if bundling is enabled.
        """
        return self._read_bool(KEY_BUNDLE_PARALLEL, DEFAULT_BUNDLE_PARALLEL)

    def set_bundle_parallel_edges(self, enabled: bool) -> None:
        """Persist the bundle-parallel-edges preference.

        Args:
            enabled: True to enable bundling.
        """
        self._write_bool(KEY_BUNDLE_PARALLEL, enabled)

    def arrow_at_middle(self) -> bool:
        """Return whether directed edges draw their arrow at the midpoint.

        Returns:
            True if arrows are drawn at the middle of the edge.
        """
        return self._read_bool(KEY_ARROW_AT_MIDDLE, DEFAULT_ARROW_AT_MIDDLE)

    def set_arrow_at_middle(self, enabled: bool) -> None:
        """Persist the arrow-at-middle preference.

        Args:
            enabled: True to draw arrows at the midpoint.
        """
        self._write_bool(KEY_ARROW_AT_MIDDLE, enabled)

    def _read_bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def _write_bool(self, key: str, value: bool) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()
