"""Tests for the application settings wrapper."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from infrastructure.settings import (
    DEFAULT_DARK_THEME,
    KEY_DARK_THEME,
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
    """Without a saved value, the default theme is returned."""
    assert app_settings.dark_theme() is DEFAULT_DARK_THEME


def test_set_dark_theme_false(app_settings: AppSettings) -> None:
    """Saving False makes dark_theme return False."""
    app_settings.set_dark_theme(False)

    assert app_settings.dark_theme() is False


def test_set_dark_theme_true(app_settings: AppSettings) -> None:
    """Saving True makes dark_theme return True."""
    app_settings.set_dark_theme(True)

    assert app_settings.dark_theme() is True


def test_round_trip_through_new_instance(qsettings: QSettings) -> None:
    """A second AppSettings on the same QSettings sees the saved value."""
    first = AppSettings(qsettings)
    first.set_dark_theme(False)

    second = AppSettings(qsettings)
    assert second.dark_theme() is False


def test_overwriting_value(qsettings: QSettings) -> None:
    """Saving a new value replaces the previous one."""
    settings = AppSettings(qsettings)
    settings.set_dark_theme(True)
    settings.set_dark_theme(False)

    assert settings.dark_theme() is False


def test_string_true_is_interpreted_as_true(qsettings: QSettings) -> None:
    """A stored string "true" is interpreted as the boolean True."""
    qsettings.setValue(KEY_DARK_THEME, "true")
    qsettings.sync()

    assert AppSettings(qsettings).dark_theme() is True


def test_string_false_is_interpreted_as_false(qsettings: QSettings) -> None:
    """A stored string "false" is interpreted as the boolean False."""
    qsettings.setValue(KEY_DARK_THEME, "false")
    qsettings.sync()

    assert AppSettings(qsettings).dark_theme() is False


def test_string_one_is_interpreted_as_true(qsettings: QSettings) -> None:
    """A stored string "1" is interpreted as the boolean True."""
    qsettings.setValue(KEY_DARK_THEME, "1")
    qsettings.sync()

    assert AppSettings(qsettings).dark_theme() is True
