# Semantic Browser

> A browser that follows meaning, not routes.

English | [日本語](./README.ja.md)

Semantic Browser browses hyperlinks by what they mean.

It is a machine client for navigating hypermedia applications autonomously.

A human browser is driven by a person who reads the representation and picks a
link. Semantic Browser is driven by a machine that reads the representation
*and the semantics it declares*, then picks one of the affordances the server
offered.

## Core concept

The client never invents an action. It chooses one, from what the server put in
front of it.

```
representation
    +
hypermedia controls
    +
semantic description (ALPS)
    ↓
semantic decision
    ↓
choose transition
    ↓
next representation
```

## Principles

- **Discovery over Configuration** — start from one entry URI and learn the
  application's shape from HAL (`_links`) and ALPS (`rel="profile"`). No route
  table, no API definition supplied in advance.
- **Server-Driven Affordances** — the client does not construct URLs or invent
  actions. It selects among the transitions the current representation offers.
- **Safety First** — `unsafe` transitions are not executed by default. `safe`
  and `idempotent` ones are preferred. *Partially implemented: the walker reads
  a `method` hint on the link, not the `type` ALPS declares. See
  [docs/M1-RESULT.md](./docs/M1-RESULT.md).*

## Decision engine

`semantic decision` is implemented with [Laya-MLX](https://github.com/mizorewww/laya-mlx).

Laya is not a text generator. It is an encoder: it takes a state and a set of
labelled options and returns **a probability for each option**. Zero output
tokens. Answering with something that was not offered is therefore not a rule
it follows — it is not expressible.

*Server-Driven Affordances* stops being a convention and becomes the shape of
the model.

API, limits and measurements: [docs/laya-mlx.md](./docs/laya-mlx.md).

## Status

**Proof of Concept — Stage 1 complete.**

The `discover → understand → choose → follow → record` loop works. Semantic
Audit turns out to need one more prerequisite.

- The browser traverses a live application using HAL and ALPS alone, with no
  prior knowledge of it
- The **deterministic** half of the audit — missing descriptions, reachability
  — is usable today, and found real defects in a third-party ALPS profile
- **Judgement based on meaning needs the instrument itself calibrated first.**
  An instrument that reports two opposite descriptions as indistinguishable
  cannot separate "this application is vague" from "this engine cannot read"

Measurements and the full account: [docs/M1-RESULT.md](./docs/M1-RESULT.md).
Implementation plan: [docs/PLAN.md](./docs/PLAN.md).

## Running it

The target application lives in a separate repository on purpose. Whoever
writes the descriptions must not be whoever reads them, or the audit grades its
own homework.

```bash
git clone https://github.com/koriym/semantic-browser-fixture
cd semantic-browser-fixture
python3 -m venv .venv && .venv/bin/pip install fastapi uvicorn
.venv/bin/uvicorn server:app --port 8791
```

```bash
python3 -m venv .venv && .venv/bin/pip install httpx laya-mlx
.venv/bin/python main.py http://127.0.0.1:8791/ \
  --goal "Find the name of the referee who argued against publishing the paper titled 'Affordance Density in Machine-Readable Hypermedia'." \
  --trace var/trace.jsonl
```

Apple Silicon, Python 3.11+. The first run downloads the checkpoint.

Every step is written to the trace: the candidates, the descriptions actually
sent to the engine, the probability over them, the links that were excluded and
why, and which checkpoint produced the numbers. A run that goes to the wrong
place says so.

## Where this is going: Semantic Audit

The point is not the browser. It is what the traversal record tells you about
the application.

| Question | How it is answered |
| --- | --- |
| **Completeness** — is every transition ALPS declares actually offered in HAL? | Set operations. Deterministic |
| **Consistency** — do the declarations match the methods and responses? | Set operations. Deterministic |
| **Reachability** — can every declared state be reached from an entry point? | Graph traversal. Deterministic |
| **Clarity** — are two affordances distinguishable from their descriptions? | Needs a calibrated instrument. Not yet |

The first three already work on an ALPS profile alone, with no server running.
On a real e-commerce profile (100 states, 208 transitions) they found 44
transitions no state offers and 15 states nothing transitions into: paths that
**no engine can take**, because the declarations do not contain them.

The fourth is the open problem, and Stage 1's main result is identifying why.
