"""Semantic Browser CLI: discover -> choose -> follow, tracing to trace.jsonl.

M1 is read-only: only GET links are ever followed, and templated links are
excluded from candidates (docs/PLAN.md, Milestone 1).
"""

import argparse
import json
import sys
from urllib.parse import urlparse

from decision import LayaMlxDecisionEngine
from walker import Walker, extract_candidates, state_digest

REACHED = 0.5


def main() -> int:
    parser = argparse.ArgumentParser(prog="semantic-browser")
    parser.add_argument("entry_uri")
    parser.add_argument("--goal", required=True, help="what the traversal should achieve")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--trace", default="trace.jsonl")
    parser.add_argument("--model", default="aac6fef/laya-mlx")
    args = parser.parse_args()

    entry = urlparse(args.entry_uri).path or "/"
    walker = Walker(args.entry_uri)
    engine = LayaMlxDecisionEngine(args.model)
    try:
        traverse(walker, engine, entry, args)
    finally:
        walker.close()
    return 0


def traverse(walker: Walker, engine: LayaMlxDecisionEngine, entry: str, args: argparse.Namespace) -> None:
    descriptors = walker.alps_descriptors(walker.profile_url(entry))

    uri = entry
    representation = walker.fetch(uri)
    visited: set[str] = set()
    history: list[str] = []
    with open(args.trace, "w") as trace:
        for step in range(args.max_steps):
            candidates, excluded = extract_candidates(representation, uri, descriptors, visited)
            state = build_state(uri, representation, history)
            decision = engine.decide(args.goal, state, candidates) if candidates else None
            reason = _stop_reason(decision)
            record = {
                "step": step,
                "uri": uri,
                "goal": args.goal,
                "state": state,
                "candidates": [
                    {"rel": c.rel, "label": c.label, "href": c.href, "description": c.description}
                    for c in candidates
                ],
                "excluded": excluded,
                "criteria": {c.label: c.description for c in candidates},
                "decision": decision,
            }
            if reason:
                reached = _goal_reached(decision) if decision is not None else False
                record["result"] = "goal_reached" if reached else "exhausted"
                record["stop_reason"] = reason
                trace.write(json.dumps(record, ensure_ascii=False) + "\n")
                outcome = "goal reached" if reached else "traversal exhausted"
                print(f"{outcome} at {uri} ({reason}, step {step + 1}/{args.max_steps})")
                return
            chosen = next(c for c in candidates if c.label == decision["choice"])
            visited.add(uri)
            history.append(uri)
            representation = walker.fetch(chosen.href)
            uri = chosen.href
            record["followed"] = chosen.href
            trace.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"step {step + 1}: {uri}")
        print(f"max steps ({args.max_steps}) reached at {uri}")


def build_state(uri: str, representation: dict, history: list[str]) -> str:
    """State is the current URI, visited URIs, and the body values. Neither the
    rel vocabulary nor the descriptor language of the page is included
    (docs/laya-mlx.md, Spike: vocabulary in the state sways the choice toward
    itself)."""
    visited = " Visited: " + ", ".join(history) if history else ""
    return f"At {uri}.{visited} {state_digest(representation)}".strip()


def _stop_reason(decision: dict | None) -> str | None:
    """Stop when nothing is left to open, or when the page answers that the
    goal is already reached. The confidence cannot gate following: the right
    candidate scores confidence 0.053 among two options and 1.0 among one,
    because it is calibrated per answer and not per candidate (measured)."""
    if decision is None:
        return "no candidates"
    if decision["reached_probability"] > REACHED:
        return f"reached {decision['reached_probability']:.3f} > {REACHED:.3f}"
    return None


def _goal_reached(decision: dict) -> bool:
    return decision["reached_probability"] > REACHED


if __name__ == "__main__":
    sys.exit(main())
