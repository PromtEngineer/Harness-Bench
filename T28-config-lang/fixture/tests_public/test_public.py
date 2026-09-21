"""Public tests — run: python3 -m pytest tests_public/ (from the ws root)."""
import subprocess
import sys

import confl


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_scalars(tmp_path):
    p = write(tmp_path, "a.confl", 'x = 3\ny = -12\nz = true\ns = "hi"\n')
    assert confl.load(p) == {"x": 3, "y": -12, "z": True, "s": "hi"}


def test_sections_nest(tmp_path):
    p = write(tmp_path, "a.confl", '[db.primary]\nhost = "h"\nport = 5\n')
    assert confl.load(p) == {"db": {"primary": {"host": "h", "port": 5}}}


def test_last_wins(tmp_path):
    p = write(tmp_path, "a.confl", 'x = 1\nx = 2\n')
    assert confl.load(p) == {"x": 2}


def test_list_and_append(tmp_path):
    p = write(tmp_path, "a.confl", 'l = [1, 2]\nl += [3]\n')
    assert confl.load(p) == {"l": [1, 2, 3]}


def test_interpolation(tmp_path):
    p = write(tmp_path, "a.confl", 'name = "world"\ng = "hello ${name}"\n')
    assert confl.load(p)["g"] == "hello world"


def test_dumps_flat():
    out = confl.dumps_flat({"b": {"x": [1, True]}, "a": "s"})
    assert out == 'a="s"\nb.x=[1,true]'


def test_example_cli():
    p = subprocess.run([sys.executable, "-m", "confl", "resolve",
                        "examples/app.confl"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    want = open("examples/app.flat").read()
    assert p.stdout == want + "\n", p.stdout


def test_error_is_conflerror(tmp_path):
    p = write(tmp_path, "a.confl", 'x = nope\n')
    try:
        confl.load(p)
        assert False, "expected ConflError"
    except confl.ConflError:
        pass
