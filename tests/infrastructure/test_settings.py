"""Tests for the application settings wrapper."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from infrastructure.settings import (
    DEFAULT_DARK_THEME,
    DEFAULT_SNAP_TO_GRID,
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


def test_round_trip_through_new_instance(qsettings: QSettings) -> None:
    """A second AppSettings sees the saved snap value."""
    first = AppSettings(qsettings)
    first.set_snap_to_grid(True)

    second = AppSettings(qsettings)
    assert second.snap_to_grid() is True


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
