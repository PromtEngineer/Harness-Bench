"""Hidden CONFL conformance tests (cwd = workspace root)."""
import os
import subprocess
import sys

import pytest

import confl


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return str(p)


def err(tmp_path, text, name="e.confl"):
    p = write(tmp_path, name, text)
    with pytest.raises(confl.ConflError) as ei:
        confl.load(p)
    return str(ei.value)


def test_escapes(tmp_path):
    p = write(tmp_path, "a.confl", r's = "\x41\t\"q\"\n\\"' + "\n")
    assert confl.load(p)["s"] == 'A\t"q"\n\\'


def test_bad_escape(tmp_path):
    assert "escape" in err(tmp_path, r's = "\q"' + "\n")
    assert "escape" in err(tmp_path, r's = "\xZZ"' + "\n")


def test_raw_string_literal(tmp_path):
    p = write(tmp_path, "a.confl", 'x = 1\ns = r"C:\\dir\\${x}#not-comment"\n')
    assert confl.load(p)["s"] == "C:\\dir\\${x}#not-comment"


def test_dollar_without_brace(tmp_path):
    p = write(tmp_path, "a.confl", 's = "cost $5"\n')
    assert confl.load(p)["s"] == "cost $5"


def test_hash_inside_string_not_comment(tmp_path):
    p = write(tmp_path, "a.confl", 's = "a#b" # real comment\n')
    assert confl.load(p)["s"] == "a#b"


def test_nested_lists(tmp_path):
    p = write(tmp_path, "a.confl", 'l = [[1, 2], [true, "s"], []]\n')
    assert confl.load(p)["l"] == [[1, 2], [True, "s"], []]


def test_empty_and_trailing_comma(tmp_path):
    p = write(tmp_path, "a.confl", 'a = []\nb = [1,]\n')
    assert confl.load(p) == {"a": [], "b": [1]}


def test_include_chain_relative(tmp_path):
    write(tmp_path, "sub/inner.confl", '[deep]\nv = 7\n')
    write(tmp_path, "sub/mid.confl", 'include "inner.confl"\nm = 1\n')
    p = write(tmp_path, "top.confl",
              '[app]\ninclude "sub/mid.confl"\nk = 2\n')
    # include resets to root inside the file; [app] restored after
    assert confl.load(p) == {"deep": {"v": 7}, "m": 1, "app": {"k": 2}}


def test_include_cycle(tmp_path):
    write(tmp_path, "a.confl", 'include "b.confl"\n')
    write(tmp_path, "b.confl", 'include "a.confl"\n')
    msg = err(tmp_path, 'include "a.confl"\n', name="root.confl")
    assert "cycle" in msg


def test_include_depth(tmp_path):
    for i in range(11):
        nxt = f'include "f{i+1}.confl"\n' if i < 10 else "x = 1\n"
        write(tmp_path, f"f{i}.confl", nxt)
    msg = err(tmp_path, 'include "f0.confl"\n', name="rootd.confl")
    assert "depth" in msg
    # 5 deep is fine
    for i in range(5):
        nxt = f'include "g{i+1}.confl"\n' if i < 4 else "y = 2\n"
        write(tmp_path, f"g{i}.confl", nxt)
    p = write(tmp_path, "rootok.confl", 'include "g0.confl"\n')
    assert confl.load(p) == {"y": 2}


def test_append_across_include(tmp_path):
    write(tmp_path, "base.confl", 'l = ["a"]\ns = "x"\n')
    p = write(tmp_path, "top.confl",
              'include "base.confl"\nl += ["b"]\ns += "y"\n')
    assert confl.load(p) == {"l": ["a", "b"], "s": "xy"}


def test_append_errors(tmp_path):
    assert "append" in err(tmp_path, 'x = 1\nx += 2\n')
    assert "append" in err(tmp_path, 'y += [1]\n')
    assert "append" in err(tmp_path, 'l = [1]\nl += "s"\n')


def test_interpolate_int_bool(tmp_path):
    p = write(tmp_path, "a.confl",
              'n = 42\nb = false\ns = "n=${n} b=${b}"\n')
    assert confl.load(p)["s"] == "n=42 b=false"


def test_interpolation_uses_final_value(tmp_path):
    p = write(tmp_path, "a.confl", 's = "v=${x}"\nx = 1\nx = 2\n')
    assert confl.load(p)["s"] == "v=2"


def test_chained_interpolation(tmp_path):
    p = write(tmp_path, "a.confl",
              'a = "A"\nb = "${a}B"\nc = "${b}C"\n')
    assert confl.load(p)["c"] == "ABC"


def test_cycle_message_exact(tmp_path):
    p = write(tmp_path, "a.confl", 'a = "${b}"\nb = "${a}"\n')
    with pytest.raises(confl.ConflError) as ei:
        confl.load(p)
    assert str(ei.value) == "interpolation cycle: a -> b -> a"


def test_self_cycle_message(tmp_path):
    p = write(tmp_path, "a.confl", 'a = "x${a}"\n')
    with pytest.raises(confl.ConflError) as ei:
        confl.load(p)
    assert str(ei.value) == "interpolation cycle: a -> a"


def test_unknown_ref(tmp_path):
    assert "unknown" in err(tmp_path, 's = "${missing.key}"\n')


def test_interpolate_list_error(tmp_path):
    assert "list" in err(tmp_path, 'l = [1]\ns = "${l}"\n')


def test_path_conflict(tmp_path):
    msg = err(tmp_path, 'a = 1\n[a]\nb = 2\n')
    assert msg == "path conflict: a"
    msg = err(tmp_path, '[a]\nb = 2\n[a.b]\nc = 3\n', name="e2.confl")
    assert msg == "path conflict: a.b"


def test_bad_keys_and_values(tmp_path):
    err(tmp_path, '9bad = 1\n')
    err(tmp_path, 'x = True\n')
    err(tmp_path, 'x = 1.5\n')
    err(tmp_path, 'x = "unterminated\n')
    err(tmp_path, 'x = [1, 2\n')
    err(tmp_path, '[bad section]\nx = 1\n')


def test_section_restored_after_include(tmp_path):
    write(tmp_path, "inc.confl", 'rootkey = 1\n')
    p = write(tmp_path, "a.confl",
              '[sec]\nx = 1\ninclude "inc.confl"\ny = 2\n')
    assert confl.load(p) == {"sec": {"x": 1, "y": 2}, "rootkey": 1}


def test_dumps_flat_shapes():
    assert confl.dumps_flat({}) == ""
    out = confl.dumps_flat({"z": True, "a": {"b": [1, "x", [2]]}})
    assert out == 'a.b=[1,"x",[2]]\nz=true'


def test_cli_error_contract(tmp_path):
    p = write(tmp_path, "bad.confl", 'x = nope\n')
    r = subprocess.run([sys.executable, "-m", "confl", "resolve", p],
                       capture_output=True, text=True, cwd=os.getcwd())
    assert r.returncode == 2
    assert r.stderr.startswith("ConflError: "), r.stderr
