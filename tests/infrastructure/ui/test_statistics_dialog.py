"""Tests for the statistics dialog."""

from collections.abc import Iterator

import pytest

from application.statistics import GraphStatistics
from infrastructure.ui.dialogs.statistics_dialog import (
    StatisticsDialog,
    _format_optional_float,
    _format_optional_int,
)


@pytest.fixture
def stats() -> GraphStatistics:
    return GraphStatistics(
        node_count=10,
        edge_count=15,
        density=0.333,
        average_degree=3.0,
        component_count=1,
        diameter=4,
        average_path_length=2.5,
    )


@pytest.fixture
def dialog(qtbot: object, stats: GraphStatistics) -> Iterator[StatisticsDialog]:
    _ = qtbot
    widget = StatisticsDialog(stats)
    yield widget
    widget.deleteLater()


def test_dialog_has_title(dialog: StatisticsDialog) -> None:
    """The dialog shows the expected window title."""
    assert dialog.windowTitle() == "Graph statistics"


def test_dialog_constructs_with_all_fields(
    dialog: StatisticsDialog,
) -> None:
    """The dialog can be constructed with a full statistics object."""
    assert dialog._form.rowCount() == 7


def test_format_optional_int_with_value() -> None:
    """An int is rendered as text."""
    assert _format_optional_int(5) == "5"


def test_format_optional_int_with_none() -> None:
    """None is rendered as n/a."""
    assert _format_optional_int(None) == "n/a"


def test_format_optional_float_with_value() -> None:
    """A float is rendered with two decimals."""
    assert _format_optional_float(2.5) == "2.50"


def test_format_optional_float_with_none() -> None:
    """None is rendered as n/a."""
    assert _format_optional_float(None) == "n/a"
