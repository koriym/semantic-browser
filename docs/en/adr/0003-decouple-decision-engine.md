# 3. Decouple Decision Engine

- Status: accepted
- Date: 2026-09-21

## Context

The core function of the Semantic Browser is to "choose" the next action among the available affordances. This choice logic initially uses `laya-mlx`, but we may later swap in a generative LLM (GPT-4, Claude, etc.) or an engine with a different approach.

This would not be a drop-in upgrade, however. `laya-mlx` does not generate text; it returns probabilities over the choices presented ([docs/laya-mlx.md](../laya-mlx.md)). Swapping in a generative LLM adds concerns that do not exist for `laya-mlx`: a mechanism to prevent outputs outside the given choices, response parsing, and handling of a reason string. These are not differences that can be hidden behind the interface, so a swap would also require revisiting the Trace format and the Audit's assumptions.

If the decision logic is tightly coupled with core logic such as HTTP communication and HAL parsing, swapping engines becomes difficult and the project loses flexibility.

## Decision

We **clearly separate** the decision engine from the Semantic Browser's core logic.

Specifically, we define an abstract interface (ABC: Abstract Base Class) as follows.

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DecisionEngine(ABC):
    @abstractmethod
    def choose_next_action(
        self,
        current_representation: Dict[str, Any],
        available_links: List[Dict[str, Any]],
        alps_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Choose one action to execute next among the available links.

        Returns:
            The dict of the chosen link. Returns None if no choice can be made.
        """
        pass
```

A concrete class such as `LayaMlxDecisionEngine` implements this interface. The core logic depends only on this interface.

## Consequences

- **Positive:**
  - **Swappability:** New decision engines can be added or swapped in easily without changing the core logic.
  - **Testability:** During testing, the decision engine can be replaced with a mock object, making unit testing of the core logic easy.
  - **Separation of concerns:** HTTP communication, hypermedia interpretation, and semantic decision-making are separated, improving code clarity.
- **Negative:**
  - A small upfront cost to define a small interface and concrete class.
