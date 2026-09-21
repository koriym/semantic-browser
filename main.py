"""Semantic Browser CLI: discover -> choose -> follow, tracing to trace.jsonl.

M1 is read-only: only GET links are ever followed, and templated links are
excluded from candidates (docs/PLAN.md, Milestone 1).
"""

import argparse
import json
import sys
from urllib.parse import urlparse

from decision import DONE_MARGIN, LayaMlxDecisionEngine
from walker import Walker, extract_candidates, state_digest


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
            candidates = extract_candidates(representation, uri, descriptors, visited)
            state = build_state(uri, representation, history, descriptors)
            decision = engine.decide(args.goal, state, candidates) if candidates else None
            stop = (
                decision is None
                or decision["done_probability"] > decision["confidence"] + DONE_MARGIN
            )
            record = {
                "step": step,
                "uri": uri,
                "goal": args.goal,
                "candidates": [
                    {"rel": c.rel, "label": c.label, "href": c.href} for c in candidates
                ],
                "decision": decision,
            }
            if stop:
                record["result"] = "goal_reached"
                trace.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"goal reached at {uri} (step {step + 1}/{args.max_steps})")
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


def build_state(uri: str, representation: dict, history: list[str], descriptors: dict[str, dict]) -> str:
    """State is the current URI, visited URIs, and a semantic digest: body
    values plus the descriptor language of what the page links to and embeds.
    The bare rel vocabulary is excluded (Spike: it sways the choice toward
    itself); the descriptor title/doc is what tells the model what a resource
    means, and a resource's meaning is its descriptors, not its field values."""
    visited = " Visited: " + ", ".join(history) if history else ""
    return f"At {uri}.{visited} {state_digest(representation, descriptors)}".strip()


if __name__ == "__main__":
    sys.exit(main())
