#!/usr/bin/env python3
"""Validate the Harness-Bench task package and checker/reference contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

from prepare_fixture import GIT_FIXTURE_SUBDIRS, prepare_fixture


ROOT = Path(__file__).resolve().parent
TASK_RE = re.compile(r"^T(\d{2})-[a-z0-9-]+$")
TIERS = {**{n: "easy" for n in range(1, 5)},
         **{n: "medium" for n in range(5, 13)},
         **{n: "hard" for n in range(13, 21)},
         **{n: "expert" for n in range(21, 41)}}
GENERATOR_TASKS = {
    1, 4, 6, 7, 8, 9, 10, 12, 13, 16, 17, 18, 19, 20, 21,
}
JUNK_NAMES = {".DS_Store", "__pycache__", ".pytest_cache"}
SUSPICIOUS_ROOT_FILES = {
    "sitecustomize.py", "sitecustomize", "usercustomize.py", "usercustomize",
    "pytest.py", "pytest", "json.py", "json", "hashlib.py", "hashlib",
    "subprocess.py", "subprocess", "pytest.ini", "tox.ini", "setup.cfg",
}


def tasks() -> list[Path]:
    return sorted(
        (path for path in ROOT.iterdir() if path.is_dir() and TASK_RE.match(path.name)),
        key=lambda path: int(TASK_RE.match(path.name).group(1)),
    )


def task_number(path: Path) -> int:
    return int(TASK_RE.match(path.name).group(1))


def yaml_scalar(path: Path, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip('"\'')
    return None


def python_candidates() -> list[str]:
    values = [sys.executable]
    for name in ("python3.12", "python3"):
        found = shutil.which(name)
        if found and found not in values:
            values.append(found)
    return values


def python_with_pytest() -> str:
    for candidate in python_candidates():
        proc = subprocess.run(
            [candidate, "-c", "import pytest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode == 0:
            return candidate
    raise RuntimeError("no Python interpreter with pytest is available")


def write_timeout_shim(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import os, signal, subprocess, sys

raw = sys.argv[1]
scale = 1
if raw.endswith("s"):
    raw = raw[:-1]
elif raw.endswith("m"):
    raw, scale = raw[:-1], 60
seconds = float(raw) * scale
proc = subprocess.Popen(sys.argv[2:], start_new_session=True)
try:
    raise SystemExit(proc.wait(timeout=seconds))
except subprocess.TimeoutExpired:
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
    raise SystemExit(124)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def checker_environment(bin_dir: Path) -> dict[str, str]:
    py = python_with_pytest()
    py_link = bin_dir / "python3"
    if not py_link.exists():
        py_link.symlink_to(py)
    timeout_link = bin_dir / "timeout"
    if not timeout_link.exists():
        write_timeout_shim(timeout_link)
    env = dict(os.environ)
    env.update({
        "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "LC_ALL": env.get("LC_ALL", "C.UTF-8"),
    })
    return env


def static_audit(selected: list[Path]) -> list[str]:
    failures: list[str] = []
    all_tasks = tasks()
    numbers = [task_number(path) for path in all_tasks]
    if numbers != list(range(1, 41)):
        failures.append(f"task numbering is not exactly T01..T40: {numbers}")

    for path in selected:
        num = task_number(path)
        for rel in (
            "prompt.txt", "fixture", "check.sh", "checker_guard.sh",
            "solution/apply.sh", "meta.yaml",
        ):
            if not (path / rel).exists():
                failures.append(f"{path.name}: missing {rel}")
        if not (path / "expected").is_dir() and not (path / "hidden").is_dir():
            failures.append(f"{path.name}: has neither expected/ nor hidden/")
        if (path / "prompt.txt").exists() and not (path / "prompt.txt").read_text().strip():
            failures.append(f"{path.name}: prompt.txt is empty")
        if (path / "fixture").is_dir() and not any((path / "fixture").iterdir()):
            failures.append(f"{path.name}: fixture/ is empty")

        meta = path / "meta.yaml"
        if meta.exists():
            if yaml_scalar(meta, "id") != f"T{num:02d}":
                failures.append(f"{path.name}: meta id must be T{num:02d}")
            if yaml_scalar(meta, "tier") != TIERS[num]:
                failures.append(f"{path.name}: tier does not match band {TIERS[num]}")
            expected_timeout = "1800" if num >= 21 else "900"
            if yaml_scalar(meta, "timeout_s") != expected_timeout:
                failures.append(
                    f"{path.name}: timeout_s must be {expected_timeout} for its band"
                )
        has_gen = (path / "gen").is_dir()
        if has_gen != (num in GENERATOR_TASKS):
            failures.append(f"{path.name}: generator provenance does not match PROVENANCE.md")

        git_archive = path / "fixture.git.tar.gz"
        if (num in GIT_FIXTURE_SUBDIRS) != git_archive.is_file():
            failures.append(f"{path.name}: nested Git fixture archive mismatch")

        check = path / "check.sh"
        if check.exists():
            check_text = check.read_text(encoding="utf-8")
            if 'CHECKER_DIR=${TASK_DIR:-}' not in check_text:
                failures.append(f"{path.name}: check.sh does not capture TASK_DIR safely")
            if 'source "$CHECKER_DIR/checker_guard.sh" || exit 1' not in check_text:
                failures.append(f"{path.name}: check.sh does not source checker_guard.sh")
            if "unset TASK_DIR" not in check_text:
                failures.append(f"{path.name}: check.sh exposes TASK_DIR to submissions")
            proc = subprocess.run(
                ["bash", "-n", str(check)], capture_output=True, text=True, check=False,
            )
            if proc.returncode:
                failures.append(f"{path.name}: check.sh syntax error: {proc.stderr.strip()}")

        guard = path / "checker_guard.sh"
        guard_template = ROOT / "_checker_guard.sh"
        if guard.exists() and guard_template.exists():
            if guard.read_bytes() != guard_template.read_bytes():
                failures.append(f"{path.name}: checker_guard.sh differs from template")

        fixture = path / "fixture"
        if fixture.is_dir():
            for name in sorted(SUSPICIOUS_ROOT_FILES):
                if (fixture / name).exists():
                    failures.append(f"{path.name}: unsafe fixture-root file: {name}")
            conftest = fixture / "conftest.py"
            if conftest.exists() and num not in {36, 40}:
                failures.append(f"{path.name}: unexpected fixture-root conftest.py")

        for source in path.rglob("*.py"):
            if any(part in JUNK_NAMES for part in source.parts):
                continue
            try:
                compile(source.read_text(encoding="utf-8"), str(source), "exec")
            except (SyntaxError, UnicodeError) as exc:
                failures.append(f"{path.name}: Python syntax/encoding error in {source}: {exc}")

    for path in ROOT.rglob("*"):
        if path.name in JUNK_NAMES or path.suffix == ".pyc":
            failures.append(f"package hygiene: generated artifact present: {path.relative_to(ROOT)}")
    return failures


def run_command(
    command: list[str], cwd: Path, env: dict[str, str], timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def stage_reference(task: Path, root: Path, env: dict[str, str]) -> Path:
    workspace = root / task.name
    prepare_fixture(task, workspace)
    task_env = dict(env, TASK_DIR=str(task))
    proc = run_command(
        ["bash", str(task / "solution" / "apply.sh")], workspace, task_env, 180,
    )
    if proc.returncode:
        raise RuntimeError(f"reference apply failed:\n{proc.stdout[-1000:]}")
    return workspace


def run_checker(
    task: Path, workspace: Path, env: dict[str, str], timeout: float = 600,
) -> subprocess.CompletedProcess[str]:
    task_env = dict(env, TASK_DIR=str(task))
    return run_command(["bash", str(task / "check.sh")], workspace, task_env, timeout)


def reference_audit(selected: list[Path]) -> list[dict]:
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="harness-bench-audit-") as temp:
        temp_root = Path(temp)
        bin_dir = temp_root / "bin"
        bin_dir.mkdir()
        env = checker_environment(bin_dir)
        for task in selected:
            started = time.monotonic()
            try:
                workspace = stage_reference(task, temp_root, env)
                proc = run_checker(task, workspace, env)
                result = {
                    "task": task.name,
                    "passed": proc.returncode == 0,
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "output_tail": proc.stdout[-1000:],
                }
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                result = {
                    "task": task.name,
                    "passed": False,
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "output_tail": str(exc)[-1000:],
                }
            results.append(result)
            print(
                f"reference {task.name}: {'PASS' if result['passed'] else 'FAIL'} "
                f"({result['elapsed_s']:.2f}s)",
                flush=True,
            )
    return results


def checker_regressions() -> list[dict]:
    probes = []
    with tempfile.TemporaryDirectory(prefix="harness-bench-regressions-") as temp:
        root = Path(temp)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        env = checker_environment(bin_dir)

        def probe(task_name: str, name: str, mutate) -> None:
            task = ROOT / task_name
            workspace = stage_reference(task, root / name, env)
            mutate(workspace)
            proc = run_checker(task, workspace, env, timeout=240)
            caught = proc.returncode != 0
            probes.append({
                "probe": name,
                "task": task_name,
                "caught": caught,
                "output_tail": proc.stdout[-800:],
            })
            print(f"regression {name}: {'PASS' if caught else 'FAIL'}", flush=True)

        def t01_nan(ws: Path) -> None:
            data = json.loads((ROOT / "T01-csv-aggregate/expected/results.json").read_text())
            for value in data.values():
                value["revenue_usd"] = float("nan")
            (ws / "results.json").write_text(json.dumps(data) + "\n")

        def t06_float_id(ws: Path) -> None:
            path = ws / "report.json"
            data = json.loads(path.read_text())
            data["q1"] = float(data["q1"])
            path.write_text(json.dumps(data) + "\n")

        def t09_trailing_blank(ws: Path) -> None:
            path = ws / "reconciled.csv"
            path.write_bytes(path.read_bytes() + b"\n")

        def t13_nan(ws: Path) -> None:
            path = ws / "violations.json"
            data = json.loads(path.read_text())
            for row in data:
                row["excess_usd"] = float("nan")
            path.write_text(json.dumps(data) + "\n")

        def t15_sequential(ws: Path) -> None:
            path = ws / "taskflow/pipeline.py"
            text = path.read_text()
            old = """        outcomes = await asyncio.gather(
            *(_process_source(name, config) for name in config.sources))"""
            new = """        outcomes = []
        for name in config.sources:
            outcomes.append(await _process_source(name, config))"""
            if old not in text:
                raise RuntimeError("T15 reference gather block changed")
            path.write_text(text.replace(old, new))

        def t16_commit(ws: Path) -> None:
            subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Audit", "-c", "user.email=audit@local",
                 "commit", "-m", "audit: forbidden commit"],
                cwd=ws, stdout=subprocess.DEVNULL, check=True,
            )

        def t38_dynamic_import(ws: Path) -> None:
            path = ws / "rx.py"
            path.write_text(path.read_text() + "\n__import__('re')\n")

        def checker_control(ws: Path) -> None:
            (ws / "sitecustomize.py").write_text(
                "raise SystemExit('checker startup was hijacked')\n"
            )

        def stdlib_module_shadow(ws: Path) -> None:
            (ws / "pathlib.py").write_text(
                "raise SystemExit('stdlib import was hijacked')\n"
            )

        def pytest_config_skip(ws: Path) -> None:
            original = ROOT / "T02-bugfix-simple/fixture/textstats/windows.py"
            shutil.copy2(original, ws / "textstats/windows.py")
            (ws / "pyproject.toml").write_text(
                '[tool.pytest.ini_options]\naddopts = "--collect-only"\n'
            )

        probe("T01-csv-aggregate", "reject-checker-control-file", checker_control)
        probe("T01-csv-aggregate", "reject-stdlib-module-shadow", stdlib_module_shadow)
        probe("T02-bugfix-simple", "ignore-project-pytest-config", pytest_config_skip)
        probe("T01-csv-aggregate", "reject-nonfinite-json", t01_nan)
        probe("T06-sqlite-report", "reject-wrong-json-types", t06_float_id)
        probe("T09-multi-csv-reconcile", "reject-nonexact-csv", t09_trailing_blank)
        probe("T13-reimbursement-audit", "reject-nonfinite-audit", t13_nan)
        probe("T15-migrate-callbacks", "require-concurrent-gather", t15_sequential)
        probe("T16-version-bump-consistency", "reject-history-change", t16_commit)
        probe("T38-regex-engine", "reject-dynamic-re-import", t38_dynamic_import)
    return probes


def select_tasks(value: str | None) -> list[Path]:
    selected = tasks()
    if not value:
        return selected
    wanted = {item.strip().upper() for item in value.split(",") if item.strip()}
    out = [path for path in selected if path.name[:3].upper() in wanted]
    missing = wanted - {path.name[:3].upper() for path in out}
    if missing:
        raise SystemExit(f"unknown task ids: {sorted(missing)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", action="store_true")
    parser.add_argument("--regressions", action="store_true")
    parser.add_argument("--tasks", help="comma-separated ids, e.g. T01,T15,T38")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    selected = select_tasks(args.tasks)
    static_failures = static_audit(selected)
    report: dict = {
        "revision": "2026-08-28-checker-hardening-2",
        "tasks_checked": len(selected),
        "static_passed": not static_failures,
        "static_failures": static_failures,
    }
    if args.references:
        refs = reference_audit(selected)
        report["references"] = refs
        report["references_passed"] = all(item["passed"] for item in refs)
    if args.regressions:
        regressions = checker_regressions()
        report["regressions"] = regressions
        report["regressions_passed"] = all(item["caught"] for item in regressions)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    ok = report["static_passed"]
    ok = ok and report.get("references_passed", True)
    ok = ok and report.get("regressions_passed", True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
