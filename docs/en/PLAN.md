# Semantic Browser: PoC Implementation Plan

This document defines a phased implementation plan for validating the Semantic Browser concept.

## 1. PoC Goal and Non-Goal

### Goal
- Prove, with a minimal setup of HAL + ALPS + Laya-MLX + HTTP traversal + Semantic Trace, that the core concept of "meaning-based navigation" is technically viable.
- Validate the project's hypothesis through a PoC scoped to a few days of work.

### Non-Goal
- Building a GUI, distributed execution, an advanced graph DB, autonomous bug fixing, or a full AI agent framework.
- Implementing a production-grade, robust authentication/authorization system.
- Supporting every hypermedia format.
- Deep dependency on BEAR.Sunday or any other specific framework.

## 2. Key Design Decisions (ADRs)

- [ADR-0001: Record Architecture Decisions](./adr/0001-record-architecture-decisions.md)
- [ADR-0002: Python as Implementation Language](./adr/0002-python-as-implementation-language.md)
- [ADR-0003: Decouple Decision Engine](./adr/0003-decouple-decision-engine.md)

## 3. Milestones

### Milestone 1: Static World Walker

- **What to build:**
  - **Mock Server:** Already provided. A peer-review journal editing system (HAL + ALPS) running at `http://127.0.0.1:8791/`. The implementer does not read this server's source. ALPS is fetched at runtime via `rel="profile"`. Keeping the writer of the descriptions separate from their reader is a precondition for Milestone 3 — reading the source would make the self-descriptiveness check self-dealing.
  - **HTTP Walker:** A client using `httpx` to extract transition candidates from HAL. There are two kinds of candidates: each `rel` under `_links`, and each `_links.self` on resources under `_embedded`. The latter is the only way to move from a list to an individual resource. Templated links containing `{id}` are excluded from candidates in M1 (expansion is Milestone 2).
  - **Decision Engine Interface:** Define a small interface such as `choose(links, alps_doc, current_state)` for invoking Laya-MLX. Candidates may mix `rel` entries and individual resources from `_embedded`, so both must be handled in a common shape.
  - **Laya-MLX Connector:** A concrete class implementing the interface above. It passes the offered `rel`s as options to a `choice` question and decides the transition from the returned probability distribution. Laya generates no text, so no parsing is needed ([docs/laya-mlx.md](./laya-mlx.md)).
  - **Traversal Loop:** The main logic driving the `discover → choose → follow` loop.
  - **Semantic Trace (JSONL):** Records each step's observations (current URI, available links, chosen link, probability distribution) to a JSONL file. Since Laya returns no reasoning text, the distribution itself is what can be kept as the basis for the choice. Also record the exact `state` string and `criteria` dict actually passed to Laya. Without these, it's impossible to later tell what the probabilities were probabilities *of*, leaving nothing for Milestone 3's Clarity check to analyze. Links excluded from the candidate set must also be recorded, along with the reason for exclusion. Silently dropping templated or unsafe links removes transitions that existed in HAL from the record, and Milestone 3's Completeness check would then miss them.

- **Definition of done:**
  - Running `python main.py <entry_uri> --goal "<goal to achieve>"` from the CLI makes the Semantic Browser traverse the server autonomously until a termination condition is met (goal reached, or max steps). `choice` is decided by matching against the goal, so a decision is undefined without one.
  - A `trace.jsonl` file is generated, holding the record of the full sequence of transitions.

- **What this validates:**
  - Whether transition candidates can be discovered from HAL and ALPS alone, with no prior knowledge.
  - Whether Laya-MLX can choose a reasonable next move based on semantic information.
  - Whether repeating this loop allows autonomous traversal of a hypermedia space.

### Milestone 2: Introducing Side Effects and Context (Stateful Traversal)

- **What to build:**
  - **Stateful Mock Server:** Extend the Mock Server so POST/PUT/DELETE change resource state (e.g., an in-memory dict).
  - **Safety Governor:** A mechanism that blocks `unsafe` transitions by default, allowing them only via a CLI flag such as `--allow-unsafe`.
  - **Context-Aware Decision:** Logic that includes the previous response body in the input to Laya-MLX and dynamically resolves path parameters (e.g., `/users/{id}`).

- **Definition of done:**
  - The Semantic Browser can autonomously execute a resource lifecycle — create (POST) → read (GET) → delete (DELETE) — through the safety mechanism.
  - The trace records either a skipped unsafe operation or one that was permitted and executed.

- **What this validates:**
  - Whether the safe/unsafe/idempotent distinction works effectively during autonomous traversal.
  - Whether context (previous state) can be read to resolve dynamic parameters.

### Milestone 3: Proto-Audit (Prototype of Semantic Audit)

- **What to build:**
  - **Trace Analyzer:** An analysis script that reads the generated `trace.jsonl` and detects semantic defects.
  - **Audit Rules:**
    - Detect "a transition defined in ALPS but absent from `_links`."
    - Detect "a transition present in `_links` but undefined in ALPS."
    - List transitions where Laya's returned probability distribution was close, as "ambiguous." As observed in [docs/laya-mlx.md](./laya-mlx.md), the distribution depends on the candidate set, so the implementer must define what counts as ambiguous and state that definition explicitly in the report.
  - **Audit Report:** Output detected defects in a human-readable format (Markdown).

- **Definition of done:**
  - Running `python analyze.py trace.jsonl` outputs a report of "semantic gaps" found in the mock server's HAL/ALPS definitions.

- **What this validates:**
  - Whether the Semantic Trace is a more meaningful behavioral record than a plain HTTP log.
  - Whether analyzing the trace can uncover defects in the application's self-descriptiveness.

## 4. Technical Uncertainty and Spikes

- **Designing state and question:** How should the `state` and `choice` question passed to Laya be structured to most reliably select the "correct `rel`"? This is typed-question design, not prompt design ([docs/laya-mlx.md](./laya-mlx.md)). **This is the single most important spike to validate first.** The "Observations (unresolved)" section of that document contains measurements of how the wording of state and the candidate set moved the outcome. No conclusion has been reached.
- **Mapping to ALPS:** How should descriptors in the ALPS document (XML/JSON) map to `choice`'s `criteria` (`{label: description}`)? This is a structural mapping, not a natural-language conversion. The context limit is 512 tokens (English checkpoint), covering instructions, criteria, and state combined. A full ALPS profile does not fit.
- **Handling rels without a description:** How should a `rel` present in `_links` but undocumented in ALPS be represented in `criteria`? Filling it in automatically would erase the very thing Milestone 3 is supposed to detect.
