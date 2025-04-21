# Copyright 2024 HorusElohim
# Licensed under the Apache License, Version 2.0

import pytest
from typing import List, Tuple

import bundle.pybind.pkgconfig as pkgconfig
from bundle.core.process import ProcessResult


@pytest.mark.parametrize(
    "cflags, exp_inc, exp_other",
    [
        ("-I/usr/include -O2 -DTEST", ["/usr/include"], ["-O2", "-DTEST"]),
        ("-Ione -Itwo", ["one", "two"], []),
    ],
)
def test_parse_cflags(cflags: str, exp_inc: List[str], exp_other: List[str]):
    inc, other = pkgconfig.parse_cflags(cflags)
    assert inc == exp_inc
    assert other == exp_other


@pytest.mark.parametrize(
    "libs, exp_libdirs, exp_libs, exp_other",
    [
        ("-L/usr/lib -lm -lpthread", ["/usr/lib"], ["m", "pthread"], []),
        ("-Lfoo -lbar -Xlinker arg", ["foo"], ["bar"], ["-Xlinker", "arg"]),
    ],
)
def test_parse_libs(libs: str, exp_libdirs: List[str], exp_libs: List[str], exp_other: List[str]):
    libdirs, libs_, other = pkgconfig.parse_libs(libs)
    assert libdirs == exp_libdirs
    assert libs_ == exp_libs
    assert other == exp_other


def test_run_pkg_config_cached_monkeypatched(monkeypatch):
    """
    Monkey-patch Process in pkgconfig so run_pkg_config_cached uses our fake results.
    """
    # Clear cache in case prior tests called it
    pkgconfig.run_pkg_config_cached.cache_clear()

    # Define a fake Process that returns predictable ProcessResults
    class FakeProc:
        def __call__(self, cmd: str, cwd=None):
            if "--cflags" in cmd:
                return ProcessResult(command=cmd, returncode=0, stdout="-Iinc1 -Iinc2 -DDEF", stderr="")
            else:
                return ProcessResult(command=cmd, returncode=0, stdout="-Llibdir -lfoo -lbar", stderr="")

    # Patch the Process class used in pkgconfig
    monkeypatch.setattr(pkgconfig, "Process", FakeProc)

    inc, cflags, libdirs, libs, lflags = pkgconfig.run_pkg_config_cached(("fakepkg",), ("d1", "d2"))

    assert inc == ["inc1", "inc2"]
    assert "-DDEF" in cflags
    assert libdirs == ["libdir"]
    assert libs == ["foo", "bar"]
    assert all(flag == "-lbar" or flag == "-lfoo" or flag.startswith("-l") for flag in lflags) or lflags == []
