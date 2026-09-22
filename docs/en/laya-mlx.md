# Laya-MLX

Facts about the library used as the decision engine. Design decisions are not recorded here.

https://github.com/mizorewww/laya-mlx · Apache-2.0 · `pip install laya-mlx`

## What it is, and what it isn't

**Not a generative model.** A bidirectional encoder encodes the state and a
typed question together, and a decision head returns probabilities.

```
state + typed question → bidirectional encoder → decision heads → probabilities
```

- **Zero output tokens.** No sentence and no JSON is generated
- Therefore **there is no string to parse.** What comes back is a Python dict
- Therefore **no reason is available.** What you get is a probability distribution
- Therefore **this is not prompt design.** What you design is how the state is written and how questions are defined

Concepts like `temperature`, `max_tokens`, grammar constraints, and streaming do not exist.

## What kind of model it is

By classification, it is **cross-encoder reranking**.

| Axis | |
| --- | --- |
| Category | **Discriminative model**, not generative |
| Architecture | **Encoder-only / bidirectional encoder**. BERT family |
| Input composition | **Cross-encoder** — encodes the state and the choices together rather than separately |
| Task shape | **Zero-shot classification / reranking** |

Calling it "LLM-based" isn't wrong (ModernBERT is also a masked language
model), but the boundary that matters isn't LLM vs. non-LLM — it's
**generative vs. discriminative** — so that label is misleading.

This classification matters because **known properties of cross-encoder
rerankers show up directly here**. Every behavior recorded under
"Observations" below matches what's already known about this kind of model.

| Observed behavior | Property of the class |
| --- | --- |
| Doesn't read negation | Typical weakness of rerankers not trained on NLI |
| Strongly drawn to surface word overlap | Expected, since it's a relevance matcher |
| Removing one candidate changes the winner | Softmax normalizes over the candidate set. IIA does not hold |
| Confidence doesn't track correctness | Calibration is over the score distribution, not over accuracy |

So swapping in a generative LLM is not a drop-in upgrade. Negation and IIA
might improve, but you lose determinism, speed, and the guarantee that
"it can't output a choice that wasn't offered." **It's a trade for a
different set of weaknesses.**

## API

```python
import laya_mlx as laya

agent = laya.load("aac6fef/laya-mlx", dtype="float16")
result = agent.predict(state, questions)
```

`state` is text, a dict, or a conversation list.
`questions` is `{name: question definition}`. Questions are evaluated independently, as a batch.

### Three question types

| type | what you specify | what comes back |
| --- | --- | --- |
| `choice` | `criteria`: `{label: description}` or a list of labels | probability and choice per label |
| `score` | `criteria`: a list of levels ordered low→high | expected level (0-indexed) and probability |
| `noul` | nothing | P(true) |

`choice` **never returns a label other than the ones presented.** Choices outside the candidate set are structurally impossible.

### An actual return value

```python
result = agent.predict(
    "Goal: list all books.",
    {"rel": {"type": "choice",
             "instructions": "Which link should I follow next?",
             "criteria": {"books": "The complete collection of books.",
                          "authors": "Every author with at least one book.",
                          "index": "The entry page of the API."}},
     "done": {"type": "noul", "instructions": "Has the goal already been reached?"}},
)
```

```python
{'model': 'laya-rl-agent',
 'answers': {
   'rel':  {'type': 'choice', 'choice': 'books', 'confidence': 0.6632,
            'probabilities': {'books': 0.9034, 'index': 0.074, 'authors': 0.0226},
            'action': {'act_probability': 1.0}},
   'done': {'type': 'noul', 'noul': 0.0834, 'confidence': 0.9166,
            'action': {'act_probability': 1.0}}},
 'usage': {'input_tokens': 91, 'output_tokens': 0}}
```

`confidence` is temperature-calibrated. `usage.input_tokens` lets you check context consumption.

## Checkpoints and limits

| Model | encoder | params | context | use |
| --- | --- | ---: | ---: | --- |
| `aac6fef/laya-mlx` | ModernBERT-large | 421M | **512** | English |
| `aac6fef/laya-multilingual-mlx` | mmBERT-base | 322M | **1024** | Multilingual |
| `aac6fef/laya-typed-decisions-mlx` | ModernBERT-large | 421M | **1024** | typed-decisions |

**The context includes all of instructions, criteria, and state combined.**
A design that passes the entire ALPS profile does not fit within 512 tokens.

Apple Silicon, Python 3.11+, macOS 14+. Weights are fetched on the first `load`.

## Speed and memory

Measured by repeating the two questions above (`rel` + `done`) 20 times.
M3 Max 96 GiB, laya-mlx 0.1.0, FP16, excluding model load.

| | |
| --- | --- |
| P50 | 17.7 ms |
| P95 | 19.5 ms |
| Peak MLX allocation | 956 MiB |

The upstream README's published figures are P50 13.4 ms for one short
question (English 421M) and 7.4 ms (multilingual 322M). Measurement
conditions differ, so these are not directly comparable to the figures above.

Unlike a generative LLM, there is no decode-speed or prefill-speed bottleneck.

## Observations (unresolved)

Measurements corresponding to the Spike in `docs/PLAN.md`. **Observations,
not conclusions.** Reproduction code is included. The judgment call is left
to the implementer.

### Checkpoint and description language

Against the fixture at `http://127.0.0.1:8791/`, a goal requiring 7 hops was
given one step at a time and correct answers were counted. The goal text used
words that appear in neither the data nor the descriptions (`referee`,
`argued against publishing`), so the task couldn't be solved by word matching.

| Checkpoint | criteria | correct | per step |
| --- | --- | ---: | ---: |
| `laya-mlx` 421M | ALPS `doc` in Japanese (drops non-ASCII, leaving only the English title) | 3/7 | 18 ms |
| `laya-mlx` 421M | Same content written in English | 5/7 | 18 ms |
| `laya-multilingual-mlx` 322M | ALPS `doc` in Japanese, as-is | **5/7** | 31 ms |

The English checkpoint doesn't handle non-ASCII well. Passing Japanese-written
ALPS to the English checkpoint effectively leaves it deciding on `title` alone.

The multilingual checkpoint's probabilities saturate (0.99–1.00 for correct
answers, 0.96 even for wrong ones). The English checkpoint stays in the
0.29–0.55 range for the same questions. **Neither confidence tracks correctness.**

### Candidates without a description

Each item under `_embedded` has no semantic route unless its collection's
`rel` has an ALPS descriptor. The implementation is then forced to pass the
raw field value.

Adding a descriptor to `review` in the fixture above moved the step of
picking the target one out of 3 reviews from 0.23 → 0.40, flipping it to
the correct answer (multilingual).

### Doesn't read negation

Common to both checkpoints. It picks candidates even when the description
explicitly negates the intended use.

| Description | Goal | Choice |
| --- | --- | --- |
| "**Not usable** for finding the reviewer of a specific manuscript" | Find the reviewer of a paper | Picked this candidate at 0.82 |
| "List of manuscripts **not yet published**" | Find a published paper | Picked this candidate at 0.79 |

### Including a URI in the state changes the choice

Same goal, same candidates; only the presence of `At /index.` at the start
of the state was varied.

| state | rank 1 |
| --- | --- |
| `At /index. Goal: list all books.` | `index` 0.912 |
| `Goal: list all books.` | `books` 0.943 |

Rewriting `index`'s description doesn't change the ranking (`index` 0.906).
Replacing labels with `option_1` etc. drops it from 0.873 → 0.422 but the
ranking doesn't change.

### Changing the candidate set changes the winner

Goal: "who wrote Norwegian Wood," no URI in the state.

| Candidates | rank 1 |
| --- | --- |
| books / authors / index | `books` 0.627 |
| books / authors | `authors` 0.601 |

Removing a seemingly unrelated candidate flips the ranking.

### Multi-step transitions are stable

Probability of choosing `author` from the state after opening a book.

| "author" word in state | rubric | result |
| --- | --- | --- |
| yes | `"author"` (fallback when ALPS lacks a description) | 0.966 |
| no | `"author"` | 0.919 |
| yes | with description | 0.989 |
| no | with description | 0.963 |

```python
import laya_mlx as laya
a = laya.load("aac6fef/laya-mlx")
crit = {"books": "The complete collection of books in the library.",
        "authors": "Every author who has written at least one book.",
        "index": "The entry page of the API."}
for s in ["At /index. Goal: list all books.", "Goal: list all books."]:
    r = a.predict(s, {"q": {"type": "choice",
                            "instructions": "Which link should I follow next?",
                            "criteria": crit}})
    print(s, r["answers"]["q"]["probabilities"])
```

## Relationship to upstream

An independent MLX port of `convaiinnovations/laya`. Weights, question
format, temperature calibration, and output schema follow upstream.
Training and fine-tuning are upstream's responsibility.
