"""Decision engine interface and Laya-MLX connector (ADR-0003)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

MAX_STATE_CHARS = 1500


@dataclass(frozen=True)
class Candidate:
    rel: str
    label: str
    href: str
    description: str
    method: str = "GET"


class DecisionEngine(ABC):
    @abstractmethod
    def decide(self, goal: str, state: str, candidates: list[Candidate]) -> dict[str, Any]:
        """Pick the candidate that best advances the goal.

        Returns the choice with its confidence and probability map, plus the
        NULP: the probability that the goal is already reached.
        """


class LayaMlxDecisionEngine(DecisionEngine):
    def __init__(self, model: str = "aac6fef/laya-mlx") -> None:
        import laya_mlx as laya

        self._agent = laya.load(model, dtype="float16")

    def decide(self, goal: str, state: str, candidates: list[Candidate]) -> dict[str, Any]:
        state = _truncate(state)
        questions = {
            "rel": {
                "type": "choice",
                "instructions": "Which link should I follow next?",
                "criteria": {c.label: c.description for c in candidates},
            },
            "reached": {
                "type": "noul",
                "instructions": "Has the goal already been reached?",
            },
        }
        state_with_goal = f"{state} Goal: {goal}"
        result = self._agent.predict(state_with_goal, questions)
        answer = result["answers"]["rel"]
        answer["reached_probability"] = result["answers"]["reached"]["noul"]
        return answer


def _truncate(state: str) -> str:
    if len(state) <= MAX_STATE_CHARS:
        return state
    return state[: MAX_STATE_CHARS - 3] + "..."
