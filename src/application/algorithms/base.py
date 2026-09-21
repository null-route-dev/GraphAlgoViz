"""Base class for step-by-step graph algorithms."""

from abc import ABC, abstractmethod

from application.algorithms.step_result import StepResult


class BaseAlgorithm(ABC):
    """Common contract for algorithms that run one visible step at a time.

    Concrete algorithms set up their state in the constructor, then
    expose ``step`` and ``is_finished``. The UI loop is:

        while not algorithm.is_finished:
            result = algorithm.step()
            render(result)

    Each call to ``step`` advances the algorithm by exactly one visible
    step and returns a snapshot describing what changed.
    """

    @property
    @abstractmethod
    def is_finished(self) -> bool:
        """Whether the algorithm has completed all its steps.

        Returns:
            True if no further steps can be taken.
        """
        raise NotImplementedError

    @abstractmethod
    def step(self) -> StepResult:
        """Advance the algorithm by one step.

        Returns:
            A snapshot describing the state after this step.

        Raises:
            RuntimeError: If the algorithm has already finished.
        """
        raise NotImplementedError
