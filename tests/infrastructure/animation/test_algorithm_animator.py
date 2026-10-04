"""Tests for the timer-driven algorithm animator."""

from collections.abc import Iterator

import pytest

from application.algorithms.base import BaseAlgorithm
from application.algorithms.step_result import StepResult
from infrastructure.animation.algorithm_animator import AlgorithmAnimator


class StubAlgorithm(BaseAlgorithm):
    """Algorithm that produces a fixed number of identifiable steps."""

    def __init__(self, num_steps: int) -> None:
        self._num_steps = num_steps
        self._current = 0

    @property
    def is_finished(self) -> bool:
        return self._current >= self._num_steps

    def step(self) -> StepResult:
        if self.is_finished:
            raise RuntimeError("Algorithm already finished")
        self._current += 1
        return StepResult(current=self._current, info=f"step {self._current}")


@pytest.fixture
def animator(qapp: object) -> Iterator[AlgorithmAnimator]:
    """Return a fresh animator, reset after the test."""
    _ = qapp
    obj = AlgorithmAnimator()
    yield obj
    obj.reset()


def test_new_animator_has_no_algorithm(animator: AlgorithmAnimator) -> None:
    """A fresh animator reports no algorithm and no history."""
    assert animator.has_algorithm is False
    assert animator.is_running is False
    assert animator.can_step_back is False
    assert animator.can_step_forward is False


def test_start_with_finished_algorithm_emits_finished(
    animator: AlgorithmAnimator,
) -> None:
    """Starting with an already-finished algorithm emits finished at once."""
    finished: list[bool] = []
    animator.finished.connect(lambda: finished.append(True))

    animator.start(StubAlgorithm(num_steps=0), interval_ms=100)

    assert finished == [True]
    assert animator.is_running is False


def test_step_forward_emits_step_ready(animator: AlgorithmAnimator) -> None:
    """step_forward emits one StepResult per call."""
    received: list[StepResult] = []
    animator.step_ready.connect(received.append)

    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()
    animator.step_forward()

    assert len(received) == 2
    assert received[0].current == 1
    assert received[1].current == 2


def test_step_back_returns_previous_state(animator: AlgorithmAnimator) -> None:
    """step_back re-emits a previously produced StepResult."""
    received: list[StepResult] = []
    animator.step_ready.connect(received.append)

    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()
    animator.step_forward()
    animator.step_back()

    assert received[-1].current == 1


def test_can_step_back_is_false_at_first_step(
    animator: AlgorithmAnimator,
) -> None:
    """After the first step, stepping back is not possible."""
    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()

    assert animator.can_step_back is False


def test_can_step_back_is_true_after_two_steps(
    animator: AlgorithmAnimator,
) -> None:
    """After two steps, stepping back is possible."""
    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()
    animator.step_forward()

    assert animator.can_step_back is True


def test_can_step_forward_is_true_until_finished(
    animator: AlgorithmAnimator,
) -> None:
    """Forward stepping is possible while there is history or work."""
    animator.start(StubAlgorithm(num_steps=2), interval_ms=100)

    assert animator.can_step_forward is True

    animator.step_forward()
    assert animator.can_step_forward is True

    animator.step_forward()
    assert animator.can_step_forward is False


def test_step_back_then_forward_replays_history(
    animator: AlgorithmAnimator,
) -> None:
    """Stepping back and forward replays without recomputing."""
    received: list[StepResult] = []
    animator.step_ready.connect(received.append)

    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()
    animator.step_forward()
    animator.step_back()
    animator.step_forward()

    assert [r.current for r in received] == [1, 2, 1, 2]


def test_start_clears_previous_history(animator: AlgorithmAnimator) -> None:
    """Starting a new algorithm discards the previous history."""
    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()
    animator.step_forward()

    animator.start(StubAlgorithm(num_steps=2), interval_ms=100)

    assert animator.can_step_back is False
    assert animator.can_step_forward is True


def test_reset_clears_everything(animator: AlgorithmAnimator) -> None:
    """reset discards the algorithm, history, and stops the timer."""
    animator.start(StubAlgorithm(num_steps=3), interval_ms=100)
    animator.step_forward()

    animator.reset()

    assert animator.has_algorithm is False
    assert animator.is_running is False
    assert animator.can_step_back is False
    assert animator.can_step_forward is False


def test_finished_emitted_at_end_of_history(
    animator: AlgorithmAnimator,
) -> None:
    """Reaching the end of the algorithm emits finished."""
    finished: list[bool] = []
    animator.finished.connect(lambda: finished.append(True))

    animator.start(StubAlgorithm(num_steps=2), interval_ms=100)
    animator.step_forward()
    animator.step_forward()

    assert finished == [True]


def test_step_forward_beyond_end_does_not_emit(
    animator: AlgorithmAnimator,
) -> None:
    """Step forward after the end does not produce new step_ready."""
    received: list[StepResult] = []
    animator.step_ready.connect(received.append)

    animator.start(StubAlgorithm(num_steps=2), interval_ms=100)
    animator.step_forward()
    animator.step_forward()
    count_at_end = len(received)
    animator.step_forward()

    assert len(received) == count_at_end
