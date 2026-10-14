"""Tests for the application settings wrapper."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from infrastructure.settings import (
    DEFAULT_ARROW_AT_MIDDLE,
    DEFAULT_BUNDLE_PARALLEL,
    DEFAULT_DARK_THEME,
    DEFAULT_SNAP_TO_GRID,
    KEY_ARROW_AT_MIDDLE,
    KEY_BUNDLE_PARALLEL,
    KEY_DARK_THEME,
    KEY_SNAP_TO_GRID,
    AppSettings,
)


@pytest.fixture
def qsettings(tmp_path: Path) -> Iterator[QSettings]:
    """Return a QSettings backed by a temporary ini file."""
    path = tmp_path / "settings.ini"
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    yield settings
    settings.clear()


@pytest.fixture
def app_settings(qsettings: QSettings) -> AppSettings:
    """Return an AppSettings bound to the temporary QSettings."""
    return AppSettings(qsettings)


def test_default_dark_theme_when_unset(app_settings: AppSettings) -> None:
    """Without a saved value, the default dark theme is returned."""
    assert app_settings.dark_theme() is DEFAULT_DARK_THEME


def test_set_dark_theme_false(app_settings: AppSettings) -> None:
    """Saving False makes dark_theme return False."""
    app_settings.set_dark_theme(False)

    assert app_settings.dark_theme() is False


def test_set_dark_theme_true(app_settings: AppSettings) -> None:
    """Saving True makes dark_theme return True."""
    app_settings.set_dark_theme(True)

    assert app_settings.dark_theme() is True


def test_default_snap_to_grid_when_unset(app_settings: AppSettings) -> None:
    """Without a saved value, the default snap setting is returned."""
    assert app_settings.snap_to_grid() is DEFAULT_SNAP_TO_GRID


def test_set_snap_to_grid_true(app_settings: AppSettings) -> None:
    """Saving True makes snap_to_grid return True."""
    app_settings.set_snap_to_grid(True)

    assert app_settings.snap_to_grid() is True


def test_set_snap_to_grid_false(app_settings: AppSettings) -> None:
    """Saving False makes snap_to_grid return False."""
    app_settings.set_snap_to_grid(False)

    assert app_settings.snap_to_grid() is False


def test_default_bundle_parallel_when_unset(app_settings: AppSettings) -> None:
    """Without a saved value, the default bundle setting is returned."""
    assert app_settings.bundle_parallel_edges() is DEFAULT_BUNDLE_PARALLEL


def test_set_bundle_parallel_true(app_settings: AppSettings) -> None:
    """Saving True makes bundle_parallel_edges return True."""
    app_settings.set_bundle_parallel_edges(True)

    assert app_settings.bundle_parallel_edges() is True


def test_set_bundle_parallel_false(app_settings: AppSettings) -> None:
    """Saving False makes bundle_parallel_edges return False."""
    app_settings.set_bundle_parallel_edges(False)

    assert app_settings.bundle_parallel_edges() is False


def test_default_arrow_at_middle_when_unset(
    app_settings: AppSettings,
) -> None:
    """Without a saved value, the default arrow setting is returned."""
    assert app_settings.arrow_at_middle() is DEFAULT_ARROW_AT_MIDDLE


def test_set_arrow_at_middle_true(app_settings: AppSettings) -> None:
    """Saving True makes arrow_at_middle return True."""
    app_settings.set_arrow_at_middle(True)

    assert app_settings.arrow_at_middle() is True


def test_set_arrow_at_middle_false(app_settings: AppSettings) -> None:
    """Saving False makes arrow_at_middle return False."""
    app_settings.set_arrow_at_middle(False)

    assert app_settings.arrow_at_middle() is False


def test_round_trip_through_new_instance(qsettings: QSettings) -> None:
    """A second AppSettings sees all saved values."""
    first = AppSettings(qsettings)
    first.set_snap_to_grid(True)
    first.set_bundle_parallel_edges(True)
    first.set_arrow_at_middle(True)

    second = AppSettings(qsettings)
    assert second.snap_to_grid() is True
    assert second.bundle_parallel_edges() is True
    assert second.arrow_at_middle() is True


def test_string_true_for_snap(qsettings: QSettings) -> None:
    """A stored string "true" is interpreted as True."""
    qsettings.setValue(KEY_SNAP_TO_GRID, "true")
    qsettings.sync()

    assert AppSettings(qsettings).snap_to_grid() is True


def test_string_false_for_dark(qsettings: QSettings) -> None:
    """A stored string "false" is interpreted as False."""
    qsettings.setValue(KEY_DARK_THEME, "false")
    qsettings.sync()

    assert AppSettings(qsettings).dark_theme() is False


def test_string_true_for_bundle(qsettings: QSettings) -> None:
    """A stored string "true" for bundle is interpreted as True."""
    qsettings.setValue(KEY_BUNDLE_PARALLEL, "true")
    qsettings.sync()

    assert AppSettings(qsettings).bundle_parallel_edges() is True


def test_string_false_for_arrow(qsettings: QSettings) -> None:
    """A stored string "false" for arrow is interpreted as False."""
    qsettings.setValue(KEY_ARROW_AT_MIDDLE, "false")
    qsettings.sync()

    assert AppSettings(qsettings).arrow_at_middle() is False
