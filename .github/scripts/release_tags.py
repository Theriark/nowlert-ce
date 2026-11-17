#!/usr/bin/env python3
"""Choose release-candidate and stable tags from the repository's own git tags.

Stdlib only and read-only: it lists tags of the checkout it runs in and prints
one JSON object. The workflows create tags; this script never does.

  next-rc --commit SHA --digest sha256:...
      The candidate tag promote-stage.yml uses for the commit Development runs.
      An unreleased annotated candidate that already seals this commit and
      digest is reused, so a re-run never mints a second tag. Otherwise it is
      the next v<version>-rc.N (a rebuilt image of a tagged commit gets a new
      N). The version is the newest one that has candidates but no stable tag
      yet, else the next minor after the newest stable 27.x release, else
      27.0.0.

  stage-candidate --commit SHA --digest sha256:...
      The candidate tag release.yml releases: the newest annotated candidate
      whose target is the stage commit and whose sealed digest is the image
      Stage runs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass

FIRST_VERSION = (27, 0, 0)
RC_RE = re.compile(r"^v(27)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-rc\.([1-9][0-9]*)$")
STABLE_RE = re.compile(r"^v(27)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class TagError(RuntimeError):
    pass


@dataclass(frozen=True)
class Tag:
    name: str
    annotated: bool
    commit: str
    message: str


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def read_tags() -> list[Tag]:
    # %00 separates fields; a record ends with %01 because messages span lines.
    out = git(
        "for-each-ref",
        "--format=%(refname:strip=2)%00%(objecttype)%00%(*objectname)"
        "%00%(objectname)%00%(contents)%01",
        "refs/tags/v27.*",
    )
    tags = []
    for record in out.split("\x01"):
        record = record.lstrip("\n")
        if not record:
            continue
        name, kind, peeled, target, message = record.split("\x00", 4)
        annotated = kind == "tag"
        tags.append(Tag(name, annotated, peeled if annotated else target, message))
    return tags


def version_of(match: re.Match[str]) -> tuple[int, int, int]:
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def text(version: tuple[int, int, int]) -> str:
    return "%d.%d.%d" % version


def sealed_digest(tag: Tag) -> str | None:
    try:
        sealed = json.loads(tag.message)
    except ValueError:
        return None
    if not isinstance(sealed, dict):
        return None
    digest = sealed.get("imageDigest")
    return digest if isinstance(digest, str) else None


def candidates(tags: list[Tag]) -> list[tuple[tuple[int, int, int], int, Tag]]:
    found = []
    for tag in tags:
        match = RC_RE.fullmatch(tag.name)
        if match:
            found.append((version_of(match), int(match.group(4)), tag))
    return sorted(found, key=lambda item: (item[0], item[1]))


def stable_versions(tags: list[Tag]) -> set[tuple[int, int, int]]:
    return {version_of(m) for t in tags if (m := STABLE_RE.fullmatch(t.name))}


def sealing(tag: Tag, commit: str, digest: str) -> bool:
    return tag.annotated and tag.commit == commit and sealed_digest(tag) == digest


def next_rc(tags: list[Tag], commit: str, digest: str) -> dict[str, object]:
    released = stable_versions(tags)
    rcs = candidates(tags)

    for version, number, tag in reversed(rcs):
        if version not in released and sealing(tag, commit, digest):
            return {"rcTag": tag.name, "version": text(version), "number": number, "reuse": True}

    # A rebuilt image of an already tagged commit gets the next number: each
    # candidate tag seals exactly one digest.
    unreleased = sorted({version for version, _, _ in rcs if version not in released})
    if unreleased:
        version = unreleased[-1]
    elif released:
        newest = max(released)
        version = (newest[0], newest[1] + 1, 0)
    else:
        version = FIRST_VERSION
    number = max((n for v, n, _ in rcs if v == version), default=0) + 1
    return {
        "rcTag": "v%s-rc.%d" % (text(version), number),
        "version": text(version),
        "number": number,
        "reuse": False,
    }


def stage_candidate(tags: list[Tag], commit: str, digest: str) -> dict[str, object]:
    matching = [item for item in candidates(tags) if sealing(item[2], commit, digest)]
    if not matching:
        raise TagError(
            f"No annotated v27 release candidate tag seals stage commit {commit} "
            f"with the Stage image digest {digest}"
        )
    version, number, tag = matching[-1]
    return {"rcTag": tag.name, "version": text(version), "number": number, "stableTag": "v" + text(version)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("next-rc", "stage-candidate"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--digest", required=True)
    args = parser.parse_args()
    try:
        if not SHA_RE.fullmatch(args.commit):
            raise TagError("--commit must be a full lowercase 40-character SHA")
        if not DIGEST_RE.fullmatch(args.digest):
            raise TagError("--digest must be sha256:<64 lowercase hex>")
        choose = next_rc if args.command == "next-rc" else stage_candidate
        print(json.dumps(choose(read_tags(), args.commit, args.digest), sort_keys=True))
        return 0
    except TagError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
