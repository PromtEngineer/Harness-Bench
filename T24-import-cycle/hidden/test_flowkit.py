"""Hidden tests for T24. Run from the workspace root (cwd = workspace)."""
import json
import os
import subprocess
import sys

WS = os.getcwd()


def run_py(code):
    return subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, cwd=WS)


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "flowkit.cli", *args],
                          capture_output=True, text=True, cwd=WS)


def test_package_imports():
    p = run_py("import flowkit")
    assert p.returncode == 0, p.stderr


def test_every_submodule_imports_standalone():
    for mod in ("pipeline", "steps", "registry", "serializers", "cli"):
        p = run_py(f"import flowkit.{mod}")
        assert p.returncode == 0, f"import flowkit.{mod} failed:\n{p.stderr}"


def test_public_api():
    p = run_py(
        "from flowkit import Pipeline, Step, build, get_registry, register\n"
        "pipe = Pipeline.from_config([{'step': 'upper'},"
        " {'step': 'prefix', 'cfg': {'prefix': '>> '}}])\n"
        "assert pipe.run('hello') == '>> HELLO', pipe.run('hello')\n"
        "assert {'upper', 'reverse', 'prefix', 'repeat'} <= set(get_registry())\n"
        "s = build('repeat', times=3)\n"
        "assert s.run('ab') == 'ababab'\n"
        "assert isinstance(s, Step)\n"
    )
    assert p.returncode == 0, p.stderr


def test_to_json_stable():
    p = run_py(
        "from flowkit import Pipeline\n"
        "pipe = Pipeline.from_config([{'step': 'prefix',"
        " 'cfg': {'prefix': 'x'}}])\n"
        "print(pipe.to_json())\n"
    )
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout)
    assert got == {"steps": [{"name": "prefix",
                              "schema": {"type": "prefix",
                                         "options": ["prefix"]}}]}, got


def test_cli_run():
    p = run_cli("run", "examples/pipeline.json", "--input", "hello world")
    assert p.returncode == 0, p.stderr
    assert p.stdout == ">> HELLO WORLD\n", repr(p.stdout)


def test_cli_list():
    p = run_cli("list")
    assert p.returncode == 0, p.stderr
    names = p.stdout.splitlines()
    assert names == sorted(names)
    assert {"prefix", "repeat", "reverse", "upper"} <= set(names)


def test_cli_describe():
    p = run_cli("describe", "examples/pipeline.json")
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout)
    assert [s["name"] for s in got["steps"]] == ["upper", "prefix"]


def test_cli_unknown_step():
    path = os.path.join(WS, ".t24_bad.json")
    with open(path, "w") as fh:
        json.dump([{"step": "nope"}], fh)
    p = run_cli("run", path, "--input", "x")
    assert p.returncode == 2, (p.returncode, p.stderr)
    assert "error: unknown step 'nope'" in p.stderr, p.stderr


def test_cli_invalid_file():
    path = os.path.join(WS, ".t24_invalid.json")
    with open(path, "w") as fh:
        fh.write("{not json")
    p = run_cli("describe", path)
    assert p.returncode == 2
    assert "error: invalid pipeline file" in p.stderr, p.stderr
    p = run_cli("run", os.path.join(WS, ".t24_missing.json"), "--input", "x")
    assert p.returncode == 2
    assert "error: invalid pipeline file" in p.stderr, p.stderr


def test_cli_bad_usage():
    assert run_cli().returncode == 2
    assert run_cli("frobnicate").returncode == 2
