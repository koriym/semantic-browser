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
                    description=intent(rel, resource, descriptors)
                    or _latinize(" ".join(str(v) for v in resource.values() if isinstance(v, (str, int, float)))),
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


def intent(rel: str, resource: dict, descriptors: dict[str, dict]) -> str | None:
    """The candidate's intention, as the ALPS descriptor states it: the goal
    wording ("Reach the editorial decision") matches descriptor language, not
    field values (measured: 0.80 vs 0.65 discrimination on the same state).
    None when no descriptor carries the meaning."""
    if rel == "self":
        return None
    doc = descriptors.get("#" + rel, {}).get("doc", {}).get("value", "")
    doc = _latinize(doc).strip().rstrip(".")
    if not doc:
        return None
    doc += "."
    identifier = next((str(value) for key, value in resource.items() if key.endswith("Id")), None)
    if identifier:
        doc = f"{doc} ({identifier})"
    return doc


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


def _latinize(text: str) -> str:
    """The English checkpoint tokenizes non-ASCII poorly; keep the latin parts."""
    kept = re.sub(r"[^\x00-\x7f]+", " ", text)
    return re.sub(r"\s+", " ", kept).strip()
