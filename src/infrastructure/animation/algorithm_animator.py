"""Timer-driven animator for step-by-step graph algorithms."""

from PySide6.QtCore import QObject, QTimer, Signal

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult

DEFAULT_INTERVAL_MS = 200
MIN_INTERVAL_MS = 50
MAX_INTERVAL_MS = 2000


class AlgorithmAnimator(QObject):
    """Drives a step-by-step algorithm on a timer.

    The animator keeps a history of every StepResult produced so far.
    This allows stepping back to replay previous states without
    recomputing them. If the user steps back and then resumes, the
    animator replays the recorded steps before computing new ones.

    The animator does not know about the canvas or the panel — it
    only reports progress through signals.

    Signals:
        step_ready: Emitted with the StepResult to render.
        finished: Emitted when the algorithm reaches its last step
            and no new steps can be computed.

    Args:
        parent: Optional Qt parent object.
    """

    step_ready = Signal(object)
    finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._algorithm: BaseAlgorithm | None = None
        self._history: list[StepResult] = []
        self._position: int = -1
        self._interval_ms = DEFAULT_INTERVAL_MS

    @property
    def is_running(self) -> bool:
        """Whether the timer is currently active.

        Returns:
            True if the algorithm is advancing automatically.
        """
        return self._timer.isActive()

    @property
    def has_algorithm(self) -> bool:
        """Whether an algorithm is currently loaded.

        Returns:
            True if an algorithm is set and not yet reset.
        """
        return self._algorithm is not None

    @property
    def can_step_back(self) -> bool:
        """Whether there is a previous state to return to.

        Returns:
            True if the displayed position is past the first step.
        """
        return self._position > 0

    @property
    def can_step_forward(self) -> bool:
        """Whether stepping forward will produce a new state.

        Returns:
            True if more history is available to replay or the
            algorithm has not yet produced its last step.
        """
        if self._algorithm is None:
            return False
        if self._position < len(self._history) - 1:
            return True
        return not self._algorithm.is_finished

    def start(self, algorithm: BaseAlgorithm, interval_ms: int) -> None:
        """Load an algorithm, clear history, and start the timer.

        If the algorithm is already finished, ``finished`` is emitted
        immediately without starting the timer.

        Args:
            algorithm: The algorithm to run.
            interval_ms: Delay between steps in milliseconds, clamped
                to the supported range.
        """
        self._algorithm = algorithm
        self._history = []
        self._position = -1
        self._interval_ms = self._clamp(interval_ms)
        if algorithm.is_finished:
            self._timer.stop()
            self.finished.emit()
            return
        self._timer.start(self._interval_ms)

    def pause(self) -> None:
        """Stop the timer without discarding the algorithm."""
        self._timer.stop()

    def resume(self) -> None:
        """Restart the timer if there is anything to advance."""
        if not self.can_step_forward:
            return
        self._timer.start(self._interval_ms)

    def step_forward(self) -> None:
        """Advance one step, replaying history if available."""
        self._timer.stop()
        self._advance()

    def step_back(self) -> None:
        """Return to the previous state in history."""
        self._timer.stop()
        if self._position <= 0:
            return
        self._position -= 1
        self.step_ready.emit(self._history[self._position])

    def reset(self) -> None:
        """Discard the current algorithm and history."""
        self._timer.stop()
        self._algorithm = None
        self._history = []
        self._position = -1

    def set_interval(self, interval_ms: int) -> None:
        """Update the step delay.

        If the timer is running, it is restarted with the new interval.

        Args:
            interval_ms: New delay between steps in milliseconds.
        """
        self._interval_ms = self._clamp(interval_ms)
        if self._timer.isActive():
            self._timer.start(self._interval_ms)

    def _advance(self) -> None:
        """Advance one step: replay if possible, compute otherwise."""
        if self._algorithm is None:
            return
        if self._position < len(self._history) - 1:
            self._position += 1
            self.step_ready.emit(self._history[self._position])
            self._maybe_finish()
            return
        if self._algorithm.is_finished:
            self._maybe_finish()
            return
        result = self._algorithm.step()
        self._history.append(result)
        self._position = len(self._history) - 1
        self.step_ready.emit(result)
        self._maybe_finish()

    def _maybe_finish(self) -> None:
        """Stop the timer and emit ``finished`` if the end is reached."""
        if self._algorithm is None:
            return
        if self._position == len(self._history) - 1 and self._algorithm.is_finished:
            self._timer.stop()
            self.finished.emit()

    def _on_tick(self) -> None:
        """Timer callback: advance by one step."""
        self._advance()

    @staticmethod
    def _clamp(value: int) -> int:
        if value < MIN_INTERVAL_MS:
            return MIN_INTERVAL_MS
        if value > MAX_INTERVAL_MS:
            return MAX_INTERVAL_MS
        return value
