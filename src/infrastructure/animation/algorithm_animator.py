"""Timer-driven animator for step-by-step graph algorithms."""

from PySide6.QtCore import QObject, QTimer, Signal

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult

DEFAULT_INTERVAL_MS = 200
MIN_INTERVAL_MS = 50
MAX_INTERVAL_MS = 2000


class AlgorithmAnimator(QObject):
    """Drives a step-by-step algorithm on a timer.

    The animator owns the QTimer and the current algorithm. It emits
    ``step_ready`` after every step and ``finished`` when the algorithm
    has no more steps. The animator does not know about the canvas or
    the panel — it only reports progress through signals.

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

    def start(self, algorithm: BaseAlgorithm, interval_ms: int) -> None:
        """Load an algorithm and start advancing it on the timer.

        If the algorithm is already finished, ``finished`` is emitted
        immediately without starting the timer.

        Args:
            algorithm: The algorithm to run.
            interval_ms: Delay between steps in milliseconds, clamped
                to the supported range.
        """
        self._algorithm = algorithm
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
        """Restart the timer if an algorithm is loaded and not finished."""
        if self._algorithm is None:
            return
        if self._algorithm.is_finished:
            return
        self._timer.start(self._interval_ms)

    def step_once(self) -> None:
        """Advance the algorithm by one step without starting the timer."""
        self._timer.stop()
        self._on_tick()

    def reset(self) -> None:
        """Discard the current algorithm and stop the timer."""
        self._timer.stop()
        self._algorithm = None

    def set_interval(self, interval_ms: int) -> None:
        """Update the step delay.

        If the timer is running, it is restarted with the new interval.

        Args:
            interval_ms: New delay between steps in milliseconds.
        """
        self._interval_ms = self._clamp(interval_ms)
        if self._timer.isActive():
            self._timer.start(self._interval_ms)

    def _on_tick(self) -> None:
        """Advance the algorithm by one step and emit the result."""
        if self._algorithm is None:
            self._timer.stop()
            return
        if self._algorithm.is_finished:
            self._timer.stop()
            self.finished.emit()
            return
        result: StepResult = self._algorithm.step()
        self.step_ready.emit(result)
        if self._algorithm.is_finished:
            self._timer.stop()
            self.finished.emit()

    @staticmethod
    def _clamp(value: int) -> int:
        if value < MIN_INTERVAL_MS:
            return MIN_INTERVAL_MS
        if value > MAX_INTERVAL_MS:
            return MAX_INTERVAL_MS
        return value
