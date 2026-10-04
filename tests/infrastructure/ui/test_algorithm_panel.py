"""Tests for the algorithm control panel."""

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QWidget

from application.algorithms.registry import build_default_registry
from infrastructure.ui.algorithm_panel import AlgorithmPanel, AlgorithmState


@pytest.fixture
def panel(qtbot: object) -> Iterator[AlgorithmPanel]:
    """Return a panel with the default algorithm registry."""
    _ = qtbot
    widget = AlgorithmPanel(build_default_registry())
    yield widget
    widget.deleteLater()


def test_new_panel_has_idle_state(panel: AlgorithmPanel) -> None:
    """A fresh panel starts in the IDLE state."""
    assert panel._state is AlgorithmState.IDLE


def test_run_disabled_without_nodes(panel: AlgorithmPanel) -> None:
    """The Run button is disabled when no nodes are available."""
    assert panel._run_button.isEnabled() is False


def test_run_enabled_after_nodes_set(panel: AlgorithmPanel) -> None:
    """The Run button becomes enabled once nodes are available."""
    panel.set_available_nodes([1, 2, 3])

    assert panel._run_button.isEnabled() is True


def test_reset_disabled_in_idle(panel: AlgorithmPanel) -> None:
    """Reset is disabled while the panel is idle."""
    assert panel._reset_button.isEnabled() is False


def test_running_state_enables_pause(panel: AlgorithmPanel) -> None:
    """In RUNNING state, Pause is enabled and Run is disabled."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.RUNNING)

    assert panel._pause_button.isEnabled() is True
    assert panel._run_button.isEnabled() is False
    assert panel._reset_button.isEnabled() is True


def test_paused_state_enables_step_buttons(panel: AlgorithmPanel) -> None:
    """In PAUSED state, step buttons reflect availability flags."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.PAUSED)
    panel.set_step_availability(can_step_back=True, can_step_forward=True)

    assert panel._step_back_button.isEnabled() is True
    assert panel._step_button.isEnabled() is True
    assert panel._pause_button.isEnabled() is False


def test_step_back_disabled_when_no_history(panel: AlgorithmPanel) -> None:
    """Back is disabled when no previous state is available."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.PAUSED)
    panel.set_step_availability(can_step_back=False, can_step_forward=True)

    assert panel._step_back_button.isEnabled() is False
    assert panel._step_button.isEnabled() is True


def test_set_available_nodes_preserves_selection(
    panel: AlgorithmPanel,
) -> None:
    """Re-populating the start node list keeps the current selection."""
    panel.set_available_nodes([1, 2, 3])
    panel._start_node_combo.setCurrentIndex(1)
    panel.set_available_nodes([1, 2, 3, 4])

    assert panel._start_node_combo.currentData() == 2


def test_run_emits_signal_with_selection(panel: AlgorithmPanel) -> None:
    """Run emits the algorithm id and start node id."""
    panel.set_available_nodes([1, 2])
    panel._start_node_combo.setCurrentIndex(1)
    received: list[tuple[str, int]] = []
    panel.run_requested.connect(lambda algo, start: received.append((algo, start)))

    panel._run_button.click()

    assert received == [("dfs", 2)]


def test_run_does_not_emit_when_disabled(panel: AlgorithmPanel) -> None:
    """A disabled Run button does not emit a request."""
    received: list[tuple[str, int]] = []
    panel.run_requested.connect(lambda algo, start: received.append((algo, start)))

    panel._run_button.click()

    assert received == []


def test_pause_emits_signal(panel: AlgorithmPanel) -> None:
    """Pause emits pause_requested when enabled."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.RUNNING)
    received: list[bool] = []
    panel.pause_requested.connect(lambda: received.append(True))

    panel._pause_button.click()

    assert received == [True]


def test_step_back_emits_signal(panel: AlgorithmPanel) -> None:
    """Back emits step_back_requested when enabled."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.PAUSED)
    panel.set_step_availability(can_step_back=True, can_step_forward=True)
    received: list[bool] = []
    panel.step_back_requested.connect(lambda: received.append(True))

    panel._step_back_button.click()

    assert received == [True]


def test_step_forward_emits_signal(panel: AlgorithmPanel) -> None:
    """Step emits step_requested when enabled."""
    panel.set_available_nodes([1])
    panel.set_state(AlgorithmState.PAUSED)
    panel.set_step_availability(can_step_back=False, can_step_forward=True)
    received: list[bool] = []
    panel.step_requested.connect(lambda: received.append(True))

    panel._step_button.click()

    assert received == [True]


def test_speed_slider_emits_interval(panel: AlgorithmPanel) -> None:
    """Changing the slider emits speed_changed with an interval."""
    received: list[int] = []
    panel.speed_changed.connect(received.append)

    panel._speed_slider.setValue(10)

    assert len(received) >= 1
    assert all(interval > 0 for interval in received)


def test_set_info_updates_label(panel: AlgorithmPanel) -> None:
    """set_info writes the given text into the info label."""
    panel.set_info("Visited node 3")

    assert panel._info_label.text() == "Visited node 3"


def test_panel_is_a_widget() -> None:
    """Sanity check: the panel is a QWidget subclass."""
    assert issubclass(AlgorithmPanel, QWidget)
