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

    Args:
        registry: Source of available algorithm metadata.
        parent: Optional Qt parent widget.
    """

    run_requested = Signal(str, int)
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
        """Update the list of node ids available as start nodes.

        Args:
            node_ids: Ids of nodes in the current graph.
        """
        current = self._start_node_combo.currentData()
        self._start_node_combo.blockSignals(True)
        self._start_node_combo.clear()
        for node_id in node_ids:
            self._start_node_combo.addItem(str(node_id), node_id)
        if current in node_ids:
            index = self._start_node_combo.findData(current)
            self._start_node_combo.setCurrentIndex(index)
        self._start_node_combo.blockSignals(False)
        self._has_nodes = bool(node_ids)
        self._update_buttons()

    def set_info(self, text: str) -> None:
        """Show a description of the last algorithm step.

        Args:
            text: The text to display.
        """
        self._info_label.setText(text)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._algorithm_combo = QComboBox(self)
        self._start_node_combo = QComboBox(self)
        form.addRow("Algorithm:", self._algorithm_combo)
        form.addRow("Start node:", self._start_node_combo)
        layout.addLayout(form)

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
        self.run_requested.emit(algorithm_id, start_node_id)

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
