"""Turns a representation into the hyperlinks it offers, each carrying the
meaning its ALPS descriptor declares. Those pairs - a link and what following
it means - are what the decision engine chooses between.

Fetches representations, extracts HAL transition candidates, and reads the
ALPS profile declared via Link: rel="profile" (M1: GET only)."""

from urllib.parse import urljoin

import httpx

from decision import Candidate


class Walker:
    def __init__(self, base_uri: str) -> None:
        self._client = httpx.Client(base_url=base_uri, timeout=10.0, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def fetch(self, uri: str) -> dict:
        response = self._client.get(uri)
        response.raise_for_status()
        return response.json()

    def profile_url(self, uri: str) -> str:
        # GET, not HEAD: the server answers GET only. The profile is declared
        # in the Link header of the representation itself.
        response = self._client.get(uri, follow_redirects=False)
        response.raise_for_status()
        for link in response.links.values():
            if link.get("rel") == "profile":
                return urljoin(uri, link["url"])
        raise NoProfile(uri)

    def alps_descriptors(self, profile_url: str) -> dict[str, dict]:
        profile = self.fetch(profile_url)
        descriptors = {}
        for descriptor in profile.get("alps", {}).get("descriptor", []):
            descriptors["#" + descriptor["id"]] = descriptor
        return descriptors


class NoProfile(Exception):
    pass


def extract_candidates(
    representation: dict,
    base_uri: str,
    descriptors: dict[str, dict],
    over_limit: set[str] = frozenset(),
) -> tuple[list[Candidate], list[dict]]:
    """Candidates are the non-self, non-templated GET links in `_links` plus
    every `_embedded` resource's `_links.self`. Returns the candidates and the
    links that exist in HAL but were not offered, each with its reason (M1:
    templated, non-GET, duplicate within the page).

    Going back is a legitimate affordance in a space with loops, so a visited
    target is not removed on sight. What is removed is a target already opened
    `REVISIT_LIMIT` times: a deterministic engine given the same state returns
    the same choice, so without a cap a wrong turn becomes a two-cycle. The cap
    is structural because a textual warning does not work - the engine does not
    read negation (docs/laya-mlx.md)."""
    candidates: list[Candidate] = []
    excluded: list[dict] = []
    seen_hrefs: set[str] = set()

    for rel, link in representation.get("_links", {}).items():
        href = urljoin(base_uri, link["href"])
        reason = None
        if rel == "self":
            reason = "self"
        elif link.get("templated"):
            reason = "templated"
        elif link.get("method", "GET").upper() != "GET":
            reason = "unsafe"
        elif href in over_limit:
            reason = "revisit-limit"
        elif href in seen_hrefs:
            reason = "duplicate"
        else:
            candidates.append(
                Candidate(
                    rel=rel,
                    label=rel,
                    href=href,
                    description=intent(rel, descriptors),
                )
            )
            seen_hrefs.add(href)
        if reason:
            excluded.append({"rel": rel, "href": href, "excluded": reason})

    for rel, resources in representation.get("_embedded", {}).items():
        for index, resource in enumerate(resources):
            self_link = resource.get("_links", {}).get("self")
            if not self_link:
                continue
            href = urljoin(base_uri, self_link["href"])
            if href in over_limit:
                excluded.append({"rel": rel, "href": href, "excluded": "revisit-limit"})
                continue
            if href in seen_hrefs:
                excluded.append({"rel": rel, "href": href, "excluded": "duplicate"})
                continue
            seen_hrefs.add(href)
            candidates.append(
                Candidate(
                    rel=rel,
                    label=f"{rel}_{index}",
                    href=href,
                    description=instance(rel, resource, descriptors),
                )
            )
    return candidates, excluded


def intent(rel: str, descriptors: dict[str, dict]) -> str:
    """What opening this link does, as the descriptor states it. The goal
    wording matches descriptor language, not field values (measured: the
    discriminator at the article hop is the description, not the URI)."""
    descriptor = descriptors.get("#" + rel)
    if not descriptor:
        return f"Follow the {rel} link."
    title = descriptor.get("title", rel)
    doc = descriptor.get("doc", {}).get("value", "")
    return f"{title}. {doc}" if doc else title


def instance(rel: str, resource: dict, descriptors: dict[str, dict]) -> str:
    """A collection's ALPS doc describes every item in it equally, so it cannot
    tell two of them apart. What distinguishes them is the body the server sent,
    and that is the only channel HAL offers here."""
    doc = descriptors.get("#" + rel, {}).get("doc", {}).get("value", "")
    fields = " ".join(
        f"{key}={value}"
        for key, value in resource.items()
        if not key.startswith("_") and isinstance(value, (str, int, float))
    )
    return f"{doc} {fields}".strip() if doc else fields


def state_digest(representation: dict) -> str:
    """Body values as key=value. The rel vocabulary and descriptor language of
    the page are excluded (docs/laya-mlx.md, Spike: vocabulary in the state
    sways the choice toward itself, and a page's offers beside the candidate
    descriptions push the goal-answered NULP toward "already reached")."""
    return " ".join(
        f"{key}={value}"
        for key, value in representation.items()
        if not key.startswith("_") and isinstance(value, (str, int, float))
    )
