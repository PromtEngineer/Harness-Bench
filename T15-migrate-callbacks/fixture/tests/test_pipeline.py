"""Behavior tests for the public taskflow API. DO NOT MODIFY.

These tests exercise only run_pipeline and the public dataclasses; they are
implementation-agnostic and must pass both before and after any internal
refactoring. Expected values derive from the documented source formula:
h = crc32(utf8(name)); count = h % 5 + 3; value_i = (h + i * 37) % 100.
"""
import zlib

import pytest

from taskflow.api import (PipelineConfig, PipelineError, PipelineResult,
                          Record, run_pipeline)


def raw_values(name):
    h = zlib.crc32(name.encode("utf-8"))
    return [(h + i * 37) % 100 for i in range(h % 5 + 3)]


def expected_records(name, multiplier=1, drop_below=0):
    recs = [Record(source=name, index=i, value=v * multiplier)
            for i, v in enumerate(raw_values(name))]
    return [r for r in recs if r.value >= drop_below]


def test_single_source_records():
    res = run_pipeline(PipelineConfig(sources=["alpha"]))
    assert isinstance(res, PipelineResult)
    assert res.records == expected_records("alpha")
    assert res.errors == []


def test_multiplier_applied():
    res = run_pipeline(PipelineConfig(sources=["alpha"], multiplier=3))
    assert res.records == expected_records("alpha", multiplier=3)


def test_drop_below_filters():
    res = run_pipeline(PipelineConfig(sources=["alpha"], drop_below=50))
    assert res.records == expected_records("alpha", drop_below=50)
    assert all(r.value >= 50 for r in res.records)


def test_multi_source_fan_out_order():
    names = ["alpha", "beta", "gamma"]
    res = run_pipeline(PipelineConfig(sources=names))
    want = []
    for n in names:
        want.extend(expected_records(n))
    assert res.records == want


def test_fail_fast_raises():
    with pytest.raises(PipelineError) as exc:
        run_pipeline(PipelineConfig(sources=["alpha", "bad:x"],
                                    fail_fast=True))
    assert "bad:x" in str(exc.value)


def test_errors_collected_without_fail_fast():
    res = run_pipeline(PipelineConfig(sources=["bad:x", "beta"],
                                      fail_fast=False))
    assert res.errors == ["bad:x: source bad:x unavailable"]
    assert res.records == expected_records("beta")


def test_empty_sources():
    res = run_pipeline(PipelineConfig(sources=[]))
    assert res.records == []
    assert res.errors == []
    assert res.summary == {"count": 0, "total": 0, "by_source": {}}


def test_summary_contents():
    names = ["alpha", "beta"]
    res = run_pipeline(PipelineConfig(sources=names))
    want = {n: len(expected_records(n)) for n in names}
    assert res.summary["by_source"] == want
    assert res.summary["count"] == sum(want.values())
    assert res.summary["total"] == sum(r.value for r in res.records)


def test_duplicate_sources_counted_separately():
    res = run_pipeline(PipelineConfig(sources=["alpha", "alpha"]))
    n = len(expected_records("alpha"))
    assert len(res.records) == 2 * n
    assert res.summary["by_source"] == {"alpha": 2 * n}


def test_invalid_multiplier_rejected():
    with pytest.raises(PipelineError) as exc:
        run_pipeline(PipelineConfig(sources=["alpha"], multiplier=0))
    assert "multiplier" in str(exc.value)
