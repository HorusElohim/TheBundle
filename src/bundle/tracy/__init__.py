# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
bundle.tracy — Tracy profiler integration for TheBundle.

When the _tracy_ext native extension is built and a Tracy viewer is connected,
all calls are live-profiled at nanosecond resolution across all threads.
When the extension is absent, every call is a silent no-op.

Usage
-----
Manual zones::

    from bundle import tracy

    with tracy.zone("load"):
        data = load()

    @tracy.zone("process")
    async def process(data): ...

Auto-instrument all Python calls::

    tracy.start()
    run_workload()
    tracy.stop()

Live metrics and annotations::

    tracy.plot("queue_size", len(q))
    tracy.message("batch complete", color=0x00FF00)
    tracy.frame_mark()
"""

from __future__ import annotations

import inspect
import os
import sys
import threading
from functools import wraps
from pathlib import Path
from typing import Any

# Normalised prefix for bundle_only filtering.
# Trailing sep avoids false matches on names that share a common prefix
# (e.g. src/bundle vs src/bundle_other).
# normcase: lower-case + backslash-normalise on Windows.
_BUNDLE_SRC = os.path.normcase(str(Path(__file__).parent.parent.resolve())) + os.sep

try:
    from . import _tracy_ext as _ext

    ENABLED = True
except ImportError:
    from . import _fallback as _ext

    ENABLED = False

# Per-thread, per-frame zone map.
#
# MUST be thread-local — not a single global dict.
#
# Rationale: CPython reuses frame objects across threads.  When thread A's
# frame is freed its memory address (id(frame)) may be immediately recycled
# for a new frame on thread B.  A global dict keyed by id(frame) would then
# map thread B's new frame to thread A's stale ZoneCtx, causing zone_end to
# be called with the wrong context on the wrong thread — Tracy's per-thread
# ring-buffer gets corrupted → Windows access violation.
#
# Coroutines reuse the same frame object across resume/suspend cycles, so
# id(frame) is still stable for the lifetime of one coroutine invocation.
# Each resume creates its own short zone; no cross-coroutine stack confusion.
_tls = threading.local()
_bundle_only: bool = False

# Source-location cache: (filename, lineno, qualname) → SrcLoc object.
#
# alloc_srcloc now returns a persistent SrcLoc (wrapping a C++
# ___tracy_source_location_data struct).  Tracy uses the pointer address as a
# stable site identifier and never frees it — so the object MUST stay alive
# as long as Tracy's Worker may reference it.  _srcloc_cache holds the only
# Python reference; it is cleared in stop() AFTER shutdown() returns (i.e.,
# after the Worker has processed every queued event).
_srcloc_cache: dict[tuple, Any] = {}


def _get_zones() -> dict:
    """Return the per-thread frame→ZoneCtx map, creating it on first access."""
    try:
        return _tls.zones
    except AttributeError:
        _tls.zones = {}
        return _tls.zones


class zone:
    """
    Tracy profiling zone — use as a context manager or decorator.

    As a context manager::

        with tracy.zone("my_zone"):
            ...

    As a decorator (sync or async)::

        @tracy.zone("my_func")
        def my_func(): ...

        @tracy.zone("my_coro")
        async def my_coro(): ...
    """

    def __init__(self, name: str, color: int = 0) -> None:
        self._name = name
        self._color = color
        self._ctx = None

    def __enter__(self) -> zone:
        if ENABLED:
            key = ("python", 0, self._name)
            srcloc = _srcloc_cache.get(key)
            if srcloc is None:
                srcloc = _ext.alloc_srcloc(0, "python", "python", self._name, self._color)
                _srcloc_cache[key] = srcloc
            self._ctx = _ext.zone_begin(srcloc)
        return self

    def __exit__(self, *args: object) -> None:
        if ENABLED and self._ctx is not None:
            _ext.zone_end(self._ctx)
            self._ctx = None

    def __call__(self, fn):  # type: ignore[override]
        name = self._name
        color = self._color
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                with zone(name, color):
                    return await fn(*args, **kwargs)

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            with zone(name, color):
                return fn(*args, **kwargs)

        return sync_wrapper


def frame_mark(name: str | None = None) -> None:
    """Emit a frame boundary marker. Optionally named for multi-frame workflows."""
    if not ENABLED:
        return
    if name:
        _ext.frame_mark_named(name)
    else:
        _ext.frame_mark()


def plot(name: str, value: float) -> None:
    """Record a live numeric value visible as a plot in the Tracy viewer."""
    if ENABLED:
        _ext.plot(name, float(value))


def message(text: str, color: int = 0) -> None:
    """Add a text annotation on the Tracy timeline. color is ARGB (0 = default)."""
    if ENABLED:
        _ext.message(text, color)


def set_thread_name(name: str) -> None:
    """Name the calling thread in the Tracy viewer."""
    if ENABLED:
        _ext.set_thread_name(name)


def is_connected() -> bool:
    """True when a Tracy viewer is actively connected."""
    return ENABLED and bool(_ext.is_connected())


# ---------------------------------------------------------------------------
# sys.setprofile hook — auto-instruments every Python call / return
# ---------------------------------------------------------------------------


def _hook(frame, event, arg):
    # CPython sets tstate->tracing++ before invoking this function, so any
    # Python calls made here (normcase, alloc_srcloc, etc.) will NOT
    # re-trigger _hook.  No manual re-entrancy guard is needed.
    ext = _ext  # capture locally — _ext may become None during interpreter shutdown
    if ext is None:
        return
    if _bundle_only and not os.path.normcase(frame.f_code.co_filename).startswith(_BUNDLE_SRC):
        return
    # Per-thread zone map — zone_begin/zone_end must pair on the same thread.
    zones = _get_zones()
    fid = id(frame)
    if event == "call":
        name = getattr(frame.f_code, "co_qualname", frame.f_code.co_name)
        key = (frame.f_code.co_filename, frame.f_lineno, name)
        srcloc = _srcloc_cache.get(key)
        if srcloc is None:
            srcloc = ext.alloc_srcloc(
                frame.f_lineno,
                frame.f_code.co_filename,
                name,
                name,
                0,
            )
            _srcloc_cache[key] = srcloc
        zones[fid] = ext.zone_begin(srcloc)
    elif event in ("return", "exception"):
        ctx = zones.pop(fid, None)
        if ctx is not None:
            ext.zone_end(ctx)


def start(bundle_only: bool = False) -> None:
    """
    Install Tracy as the global Python profiler.

    Every Python function call and return will open/close a Tracy zone,
    giving a full call-stack timeline across all threads with zero manual
    annotation.  Overhead is ~255 ns/call (Python profiler API) + ~18 ns
    (Tracy zone).

    Args:
        bundle_only: When True, only profile frames whose source file lives
                     inside the bundle package, skipping stdlib and third-party
                     libraries.  Greatly reduces noise in the Tracy viewer.
    """
    global _bundle_only
    if not ENABLED:
        return
    _bundle_only = bundle_only
    sys.setprofile(_hook)
    # threading.setprofile intentionally omitted: background threads
    # (logging, asyncio executor, ZMQ) trigger Tracy ring-buffer
    # initialisation for new threads after the viewer connects, which
    # crashes on Windows.  All interesting test code runs on the main thread.


def stop() -> None:
    """Remove the Tracy profiler hook and flush all pending data to tracy-capture."""
    sys.setprofile(None)
    try:
        _tls.zones.clear()
    except AttributeError:
        pass
    # SrcLoc strings are copied into the alloc buffer inside zone_begin, so
    # clearing the cache here is safe — Tracy holds no pointers into SrcLoc.
    _srcloc_cache.clear()
    if ENABLED:
        _ext.shutdown()
