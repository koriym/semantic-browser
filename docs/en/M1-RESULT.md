# Milestone 1: PoC Result

We checked whether `discover → understand → choose → follow → record` holds
together. It does. But we found that **Semantic Audit needs one more
precondition**.

## What we built

| | |
| --- | --- |
| Semantic Browser | This repository. `walker.py` / `decision.py` / `main.py` |
| Decision engine | [Laya-MLX](./laya-mlx.md). Generates no text; returns probabilities over the offered choices |
| Target application | [semantic-browser-fixture](https://github.com/koriym/semantic-browser-fixture). A peer-review journal (HAL + ALPS). The implementer wrote this without reading its source, using only HTTP and the ALPS fetched at runtime |

## Answers to the validation questions

| Question from `docs/PLAN.md` | Answer |
| --- | --- |
| Can transition candidates be discovered from HAL and ALPS alone, with no prior knowledge? | **Yes** |
| Can the loop repeat to traverse autonomously? | **Yes** |
| Can Laya choose a reasonable next move based on semantic information? | **Conditional. See below** |

The third question didn't come down to a simple yes/no. On the same 7-hop
task, the score moved between 3/7 and 5/7 depending on the conditions. What
mainly drove that was **whether the description reached the engine**, not
how smart the engine is.

- When ALPS `doc` is in Japanese and the English checkpoint is used, non-ASCII
  is dropped. The decision effectively rests on `title` alone: 3/7
- Passing the same description to the multilingual checkpoint: 5/7
- Collection items have no semantic route unless their collection's `rel`
  has a descriptor

Run end-to-end, it misses on the very first step. The description of the
candidate it picked reads:

> Open the roster of people who can be asked to review. **Not usable for
> finding the reviewer of a specific manuscript.**

## Properties of the engine we reproduced

All deterministic (identical input, five runs, exact match). Not model noise.

| | |
| --- | --- |
| **Doesn't read negation** | Picks a candidate described as "not usable for..." at 0.82, and "not yet published" at 0.79 |
| **Probability depends on the candidate set** | Removing one seemingly unrelated candidate flips the winner (0.627 → 0.601, reversed) |
| **Confidence doesn't track correctness** | Returns 0.96 for a wrong answer, 0.29 for a correct one |
| **Writing a URI into the state breaks the choice** | Surface-level match between label and route. Rewriting the description doesn't fix it |

That last point means the README's *"follows meaning, not routes"* is not
only a policy statement but also **an operating condition**.

These aren't model-specific defects; they're **known properties of the
cross-encoder reranking class of model** ([docs/laya-mlx.md](./laya-mlx.md)).
Knowing the classification up front would have predicted the negation issue
and the candidate-set dependency.

## Known limitation: Safety First doesn't see the declaration yet

The README states that "`unsafe` methods are not executed by default," but
the implementation only looks at the `method` property on a HAL link
(`walker.py`).

**HAL has no `method` property.** That branch only works because this PoC's
target application happens to emit one. Pointed at a real API, it would
filter nothing.

The declared safety lives in ALPS's `type` (`safe` / `idempotent` / `unsafe`),
and the code never reads it anywhere. And **whether ALPS's `type` matches the
actual HTTP method** is exactly the Consistency check described below as
"deterministic and usable right now." The implementation only looks at one
side of that pair.

## The missing precondition for Semantic Audit

To measure self-descriptiveness, the instrument must first be shown to
**distinguish well-described things from poorly-described ones**. That hasn't
been shown yet.

We tried it against a real application's ALPS: the profile of an e-commerce
app built with BEAR.Sunday (100 states / 208 transitions). **This app was
never started.** It requires a database, so only `alps.json` was targeted; no
traversal was performed.

For each transition, we turned its `title` into a question and measured
whether `laya-multilingual-mlx` (322M) could pick it back out from its
siblings' `doc` text, flagging any pair scoring under a 0.10 margin as
"confusable." 48 pairs came up.

But reading them, the claim doesn't hold.

```
goShoppingError  safe    Redirected here on errors such as insufficient stock or failed payment
doCheckout       unsafe  Executes tax/shipping calculation, inventory allocation, and point deduction, then finalizes payment
```

**Two opposites** come back as "indistinguishable" at margin −0.90. What was
actually being measured wasn't the ambiguity of the description — it was the
322M encoder's matching ability.

This instrument cannot separate `the app's description is ambiguous` from
`the engine can't read it`. **An uncalibrated instrument must not be used to
grade someone else's code.**

## Instrument-independent audits do work

Checks that are pure set operations over the same ALPS run without starting
a server, produce deterministic results, and don't depend on engine
performance.

| Check | Result |
| --- | --- |
| Missing `doc` / `title` / `rt` | All 208 transitions complete. **Zero** |
| Transitions never offered from any state | **44 / 208** |
| States with zero incoming transitions | **15 / 100** |

The latter two are claims that "no path exists in the set of declarations" —
**unreachable regardless of which engine is used.** They are structural, not
measurements.

(Restricting the entry point to `Top` reports "66 unreachable," but the admin
screen has `AdminLogin` as a separate entry point. Getting the set of entry
points wrong would report an intentional separation as a defect.)

## Conclusion of this PoC

**The browser works. Of the audit, only the deterministic part is usable
right now.**

Using meaning-based judgment for auditing requires calibrating the
instrument first: prepare known-good and known-bad descriptions, show the
instrument separates them, and only then point it at an unknown application.
That goes in before Milestone 3.

## Lessons from the work

The mistake repeated most often in this PoC wasn't a model failure or an
implementation bug — it was **reading a property of the instrument as a
property of the target**. It happened 7 times.

- Checked the effect of a constraint while the correct answer was still among the candidates
- Evaluated the score while the answer's word was still left in the state
- Evaluated the score while the goal text still contained the same words as the data
- Concluded "meaning can't be interpreted" without showing the description to the engine
- Asked "was it reached" about a fact that doesn't exist on the page
- Turned a candidate's own description directly into the question, measuring string identity
- Was about to report opposite descriptions as "confusable"

In every case, **the test was built so it didn't have to discriminate**. The
subject of a self-descriptiveness audit demands the same discipline of
itself.
