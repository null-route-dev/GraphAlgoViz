"""Control panel for running graph algorithms."""

from enum import Enum, auto

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from application.algorithms.registry import AlgorithmRegistry

SLIDER_MIN = 1
SLIDER_MAX = 20
SLIDER_DEFAULT = 5
BASE_INTERVAL_MS = 1000
MIN_INTERVAL_MS = 50

TARGET_ROW_INDEX = 2


class AlgorithmState(Enum):
    """Visual state of the algorithm controls."""

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


class AlgorithmPanel(QWidget):
    """Controls for selecting and running a graph algorithm.

    The panel emits signals describing user intent. It does not call
    use cases or animate anything itself — that is the main window's
    responsibility. The panel reflects state set by the caller through
    ``set_state`` and ``set_step_availability``.

    The target node selector is shown only when the selected algorithm
    requires a target. Which algorithms require one is read from the
    algorithm registry.

    Args:
        registry: Source of available algorithm metadata.
        parent: Optional Qt parent widget.
    """

    run_requested = Signal(str, int, object)
    pause_requested = Signal()
    step_requested = Signal()
    step_back_requested = Signal()
    reset_requested = Signal()
    speed_changed = Signal(int)

    def __init__(
        self,
        registry: AlgorithmRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._state = AlgorithmState.IDLE
        self._has_nodes = False
        self._can_step_back = False
        self._can_step_forward = False
        self._requires_target = False
        self._build_ui()
        self._populate_algorithms()
        self._update_buttons()

    def set_state(self, state: AlgorithmState) -> None:
        """Update the panel to reflect the given algorithm state.

        Args:
            state: The state to display.
        """
        self._state = state
        self._update_buttons()

    def set_step_availability(
        self,
        can_step_back: bool,
        can_step_forward: bool,
    ) -> None:
        """Update which step buttons are usable.

        Args:
            can_step_back: True if a previous state is available.
            can_step_forward: True if a next state is available or
                can still be computed.
        """
        self._can_step_back = can_step_back
        self._can_step_forward = can_step_forward
        self._update_buttons()

    def set_available_nodes(self, node_ids: list[int]) -> None:
        """Update the start and target node lists.

        Args:
            node_ids: Ids of nodes in the current graph.
        """
        self._replace_combo_items(self._start_node_combo, node_ids)
        self._replace_combo_items(self._target_node_combo, node_ids)
        self._has_nodes = bool(node_ids)
        self._update_buttons()

    def set_info(self, text: str) -> None:
        """Show a description of the last algorithm step.

        Args:
            text: The text to display.
        """
        self._info_label.setText(text)

    def _replace_combo_items(self, combo: QComboBox, node_ids: list[int]) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for node_id in node_ids:
            combo.addItem(str(node_id), node_id)
        if current in node_ids:
            index = combo.findData(current)
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._form = QFormLayout()
        self._algorithm_combo = QComboBox(self)
        self._start_node_combo = QComboBox(self)
        self._target_node_combo = QComboBox(self)
        self._form.addRow("Algorithm:", self._algorithm_combo)
        self._form.addRow("Start node:", self._start_node_combo)
        self._form.addRow("Target node:", self._target_node_combo)
        layout.addLayout(self._form)

        buttons = QHBoxLayout()
        self._run_button = QPushButton("Run", self)
        self._pause_button = QPushButton("Pause", self)
        self._step_back_button = QPushButton("Back", self)
        self._step_back_button.setToolTip("Step back")
        self._step_button = QPushButton("Step", self)
        self._step_button.setToolTip("Step forward")
        self._reset_button = QPushButton("Reset", self)
        for button in (
            self._run_button,
            self._pause_button,
            self._step_back_button,
            self._step_button,
            self._reset_button,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self._run_button.clicked.connect(self._emit_run)
        self._pause_button.clicked.connect(self._emit_pause)
        self._step_back_button.clicked.connect(self._emit_step_back)
        self._step_button.clicked.connect(self._emit_step)
        self._reset_button.clicked.connect(self._emit_reset)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:", self))
        self._speed_slider = QSlider(self)
        self._speed_slider.setMinimum(SLIDER_MIN)
        self._speed_slider.setMaximum(SLIDER_MAX)
        self._speed_slider.setValue(SLIDER_DEFAULT)
        self._speed_slider.valueChanged.connect(self._emit_speed)
        speed_row.addWidget(self._speed_slider)
        layout.addLayout(speed_row)

        self._info_label = QLabel("", self)
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

        layout.addStretch(1)

    def _populate_algorithms(self) -> None:
        for info in self._registry.all():
            self._algorithm_combo.addItem(info.display_name, info.id)
        self._algorithm_combo.currentIndexChanged.connect(self._on_algorithm_changed)
        self._update_target_visibility()

    def _on_algorithm_changed(self, _index: int) -> None:
        self._update_target_visibility()

    def _update_target_visibility(self) -> None:
        algorithm_id = self._algorithm_combo.currentData()
        requires_target = False
        if isinstance(algorithm_id, str):
            try:
                requires_target = self._registry.get(algorithm_id).requires_target
            except KeyError:
                requires_target = False
        self._requires_target = requires_target
        self._form.setRowVisible(TARGET_ROW_INDEX, requires_target)

    def _update_buttons(self) -> None:
        state = self._state
        has_nodes = self._has_nodes
        is_loaded = state in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        )
        run_enabled = (state is AlgorithmState.IDLE and has_nodes) or (
            is_loaded and self._can_step_forward
        )
        self._run_button.setEnabled(run_enabled)
        self._pause_button.setEnabled(state is AlgorithmState.RUNNING)
        self._step_back_button.setEnabled(is_loaded and self._can_step_back)
        self._step_button.setEnabled(is_loaded and self._can_step_forward)
        self._reset_button.setEnabled(state is not AlgorithmState.IDLE)

    def _emit_run(self) -> None:
        algorithm_id = self._algorithm_combo.currentData()
        start_node_id = self._start_node_combo.currentData()
        if not isinstance(algorithm_id, str):
            return
        if not isinstance(start_node_id, int):
            return
        target: int | None = None
        if self._requires_target:
            target_node_id = self._target_node_combo.currentData()
            if not isinstance(target_node_id, int):
                return
            target = target_node_id
        self.run_requested.emit(algorithm_id, start_node_id, target)

    def _emit_pause(self) -> None:
        self.pause_requested.emit()

    def _emit_step(self) -> None:
        self.step_requested.emit()

    def _emit_step_back(self) -> None:
        self.step_back_requested.emit()

    def _emit_reset(self) -> None:
        self.reset_requested.emit()

    def _emit_speed(self, value: int) -> None:
        interval_ms = max(MIN_INTERVAL_MS, BASE_INTERVAL_MS // value)
        self.speed_changed.emit(interval_ms)
