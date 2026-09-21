#!/usr/bin/env python3
"""Create the exact agent workspace for one Harness-Bench task."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import tarfile


ROOT = Path(__file__).resolve().parent
TASK_RE = re.compile(r"^T(\d{2})-[a-z0-9-]+$")
GIT_FIXTURE_SUBDIRS = {7: "pricer", 16: ".", 31: "webshop"}


def resolve_task(task_id: str) -> Path:
    normalized = task_id.upper()
    if not re.fullmatch(r"T\d{2}", normalized):
        raise ValueError(f"task id must look like T07, got {task_id!r}")
    matches = sorted(ROOT.glob(f"{normalized}-*"))
    if len(matches) != 1:
        raise ValueError(f"expected one task for {normalized}, found {len(matches)}")
    return matches[0]


def prepare_fixture(task: Path, destination: Path) -> None:
    """Copy fixture/ and restore archived nested Git metadata when required."""
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")
    shutil.copytree(task / "fixture", destination)

    match = TASK_RE.match(task.name)
    if not match:
        raise ValueError(f"invalid task directory name: {task.name}")
    number = int(match.group(1))
    subdir = GIT_FIXTURE_SUBDIRS.get(number)
    if subdir is None:
        return

    archive = task / "fixture.git.tar.gz"
    if not archive.is_file():
        raise FileNotFoundError(f"missing nested Git fixture archive: {archive}")
    target = destination / subdir
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members or any(
            member.name != ".git" and not member.name.startswith(".git/")
            for member in members
        ):
            raise ValueError(f"unsafe member in {archive}")
        bundle.extractall(target, members=members, filter="data")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="task id, for example T07")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare_fixture(resolve_task(args.task), args.destination.resolve())
    print(args.destination.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
