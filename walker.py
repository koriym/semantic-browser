"""HTTP walker: fetch representations, extract HAL transition candidates,
fetch the ALPS profile declared via Link: rel="profile" (M1: GET only)."""

import re
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
    exclude_hrefs: set[str] = frozenset(),
) -> list[Candidate]:
    """Candidates are the non-self, non-templated _links entries plus every
    _embedded resource's _links.self (M1: templated links are excluded)."""
    candidates: list[Candidate] = []
    seen_hrefs: set[str] = set(exclude_hrefs)

    for rel, link in representation.get("_links", {}).items():
        if rel == "self" or link.get("templated"):
            continue
        if link.get("method", "GET").upper() != "GET":
            continue
        href = urljoin(base_uri, link["href"])
        if href in seen_hrefs:
            continue
        candidates.append(
            Candidate(rel=rel, label=rel, href=href, description=describe(rel, descriptors))
        )
        seen_hrefs.add(href)

    for rel, resources in representation.get("_embedded", {}).items():
        for index, resource in enumerate(resources):
            self_link = resource.get("_links", {}).get("self")
            if not self_link:
                continue
            href = urljoin(base_uri, self_link["href"])
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            candidates.append(
                Candidate(
                    rel=rel,
                    label=f"{rel}_{index}",
                    href=href,
                    description=identify(rel, resource),
                )
            )
    return candidates


def describe(rel: str, descriptors: dict[str, dict]) -> str:
    descriptor = descriptors.get("#" + rel)
    if not descriptor:
        return f"Follow the {rel} link."
    title = descriptor.get("title", rel)
    doc = descriptor.get("doc", {}).get("value", "")
    text = f"{title}. {doc}" if doc else title
    return _latinize(text)


def identify(rel: str, resource: dict) -> str:
    """The candidate's own sentence: what it is, and what distinguishes it.
    A bare value per body field discriminates best (measured: p=0.938 vs 0.56
    for key=value prose)."""
    return _latinize(" ".join(str(value) for value in resource.values() if isinstance(value, (str, int, float))))


def state_digest(representation: dict, descriptors: dict[str, dict]) -> str:
    """Body values as key=value, plus the descriptor language of what the page
    links to and embeds. The bare rel vocabulary is excluded (docs/laya-mlx.md,
    Spike: vocabulary in the state sways the choice toward itself); the
    descriptor title and doc are different: they say what a resource means,
    and a page's meaning is its descriptors, not its field values."""
    body = " ".join(
        f"{key}={value}"
        for key, value in representation.items()
        if not key.startswith("_") and isinstance(value, (str, int, float))
    )
    return body + meanings(representation, descriptors)


def meanings(representation: dict, descriptors: dict[str, dict]) -> str:
    parts = [describe(rel, descriptors) for rel in representation.get("_links", {}) if rel != "self"]
    for rel in representation.get("_embedded", {}):
        parts.append(describe(rel, descriptors))
    unique = " | ".join(dict.fromkeys(p for p in parts if p))
    return " This page offers: " + unique if unique else ""


def _latinize(text: str) -> str:
    """The English checkpoint tokenizes non-ASCII poorly; keep the latin parts."""
    kept = re.sub(r"[^\x00-\x7f]+", " ", text)
    return re.sub(r"\s+", " ", kept).strip()
