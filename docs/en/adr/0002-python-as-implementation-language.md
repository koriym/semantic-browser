# 2. Python as Implementation Language

- Status: accepted
- Date: 2026-09-21

## Context

We need to choose a language to implement the Semantic Browser PoC. Candidates include Python, TypeScript (Node.js), and Go.

## Decision

We choose **Python** as the PoC's implementation language.

The reasons are as follows.

1.  **Affinity with the decision engine:** `laya-mlx`, our initial decision-engine candidate, is a Python library, and the MLX framework is also part of the Python ecosystem. This makes engine integration smoothest. `laya-mlx` does not generate text; it is an encoder that returns probabilities for typed questions ([docs/laya-mlx.md](../laya-mlx.md)). It is Apple Silicon only, so this choice also fixes the runtime environment.
2.  **HTTP and data handling:** Mature libraries such as `httpx` and `pydantic` make asynchronous HTTP communication and structured data handling easy.
3.  **Rapid prototyping:** Dynamic typing and a rich standard library suit small, fast-changing development like a PoC.

## Consequences

- **Positive:**
  - Integration with `laya-mlx` becomes easy, letting us focus on the PoC's central problem.
  - Development speed improves, enabling short-cycle hypothesis testing.
- **Negative:**
  - Compared to statically typed languages (TypeScript, Go), maintainability and performance may suffer as the codebase grows. At the PoC stage, we judge this risk to be limited.
