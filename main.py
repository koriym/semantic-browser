"""Semantic Browser CLI: discover -> choose -> follow, tracing to trace.jsonl.

M1 is read-only: only GET links are ever followed, and templated links are
excluded from candidates (docs/en/PLAN.md, Milestone 1).
"""

import argparse
import json
import sys
from urllib.parse import urlparse

from decision import MAX_STATE_CHARS, LayaMlxDecisionEngine
from walker import Walker, extract_candidates, state_digest

REACHED = 0.5


def main() -> int:
    parser = argparse.ArgumentParser(prog="semantic-browser")
    parser.add_argument("entry_uri")
    parser.add_argument("--goal", required=True, help="what the traversal should achieve")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--trace", default="trace.jsonl")
    parser.add_argument("--model", default="aac6fef/laya-multilingual-mlx")
    args = parser.parse_args()

    entry = urlparse(args.entry_uri).path or "/"
    walker = Walker(args.entry_uri)
    engine = LayaMlxDecisionEngine(args.model)
    try:
        traverse(walker, engine, entry, args)
    finally:
        walker.close()
    return 0


RULED_OUT_KEPT = 3
REVISIT_LIMIT = 2


def traverse(walker: Walker, engine: LayaMlxDecisionEngine, entry: str, args: argparse.Namespace) -> None:
    descriptors = walker.alps_descriptors(walker.profile_url(entry))

    uri = entry
    representation = walker.fetch(uri)
    visits: dict[str, int] = {}
    ruled_out: list[str] = []
    with open(args.trace, "w") as trace:
        for step in range(args.max_steps):
            visits[uri] = visits.get(uri, 0) + 1
            candidates, excluded = extract_candidates(
                representation, uri, descriptors,
                {href for href, n in visits.items() if n >= REVISIT_LIMIT},
            )
            state, truncated = build_state(representation, ruled_out)
            decision = engine.decide(args.goal, state, candidates) if candidates else None
            reason = _stop_reason(decision)
            record = {
                "step": step,
                "uri": uri,
                "goal": args.goal,
                "model": args.model,
                "state": state,
                "state_truncated": truncated,
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
            ruled_out.append(chosen.description)
            representation = walker.fetch(chosen.href)
            uri = chosen.href
            record["followed"] = chosen.href
            trace.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"step {step + 1}: {uri}")
        print(f"max steps ({args.max_steps}) reached at {uri}")


def build_state(representation: dict, ruled_out: list[str]) -> tuple[str, bool]:
    """What is known, not where we are. URIs are excluded: the engine matches
    a label against the route in the state and follows it back (docs/en/laya-mlx.md).

    Transitions already taken are listed by what they offered, so that opening
    them again is visibly redundant. Only the last few are kept: the whole state
    must fit the checkpoint's context together with the criteria, and a state
    that grows every hop silently loses its tail."""
    tried = ""
    if ruled_out:
        recent = ruled_out[-RULED_OUT_KEPT:]
        tried = " Already tried, without reaching the goal: " + " | ".join(recent) + "."
    state = f"{state_digest(representation)}{tried}".strip()
    return state, len(state) > MAX_STATE_CHARS


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
