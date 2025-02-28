#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from typing import Callable, Any

import bundle
from bundle.core import tracer, logger

MAX_SL = 15


# --------------------------
# Custom Logging Handler
# --------------------------
class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def setup_logging() -> ListHandler:
    handler = ListHandler()
    # Clear existing handlers from bundle and tracer loggers.
    bundle.BUNDLE_LOGGER.handlers.clear()
    tracer.log.handlers.clear()
    tracer.log.addHandler(handler)
    tracer.log.setLevel(logging.DEBUG)
    return handler


def print_mapping(title: str, mapping: dict[int, tuple[str, str, bool]]) -> None:
    print(f"\n{title}:")
    for sl, (func, file, hit) in mapping.items():
        marker = "* " if hit else "  "
        print(f"{marker}SL {sl:2}: caller = {func:<25} file = {file}")
    print()


def iterate_stacklevels(
    scenario: str, maker: Callable[[int], Callable[[], Any]], is_async: bool, expected: str, handler: ListHandler
) -> dict[int, tuple[str, str, bool]]:
    mapping = {}
    for sl in range(0, MAX_SL):
        handler.records.clear()
        fn = maker(sl)
        # Call the candidate function; if async, run it.
        val = fn()
        if is_async and asyncio.iscoroutine(val):
            _ = asyncio.run(val)
        else:
            _ = val
        if not handler.records:
            continue
        rec = handler.records[-1]
        mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
        if rec.funcName == expected:
            break
    print_mapping(f"Scenario {scenario}", mapping)
    return mapping


# --------------------------
# Dummy target functions
# --------------------------
def sync_success(x: int, y: int) -> int:
    return x + y


async def async_success(x: int, y: int) -> int:
    return x * y


# --------------------------
# Calibration functions for synchronous variants
# --------------------------
def calibrate_sync_call(handler: ListHandler) -> int:
    expected = "calibrate_sync_call"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()
        # Call tracer.Sync.call with sync_success
        result, exc = tracer.Sync.call(sync_success, 2, 3, stacklevel=sl)
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_sync_call mapping", mapping)
    print(f"calibrate_sync_call: Final candidate SL = {candidate}")
    return candidate


def calibrate_sync_call_raise(handler: ListHandler) -> int:
    expected = "calibrate_sync_call_raise"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()
        try:
            result = tracer.Sync.call_raise(sync_success, 2, 3, stacklevel=sl)
        except Exception:
            pass
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_sync_call_raise mapping", mapping)
    print(f"calibrate_sync_call_raise: Final candidate SL = {candidate}")
    return candidate


def calibrate_sync_decorated_call(handler: ListHandler) -> int:
    expected = "calibrate_sync_decorated_call"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()

        @tracer.Sync.decorator.call(stacklevel=sl)
        def dummy_decorated() -> int:
            return sync_success(2, 3)

        result, exc = dummy_decorated()
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_sync_decorated_call mapping", mapping)
    print(f"calibrate_sync_decorated_call: Final candidate SL = {candidate}")
    return candidate


def calibrate_sync_decorated_call_raise(handler: ListHandler) -> int:
    expected = "calibrate_sync_decorated_call_raise"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()

        @tracer.Sync.decorator.call_raise(stacklevel=sl)
        def dummy_decorated() -> int:
            return sync_success(2, 3)

        try:
            result = dummy_decorated()
        except Exception:
            pass
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_sync_decorated_call_raise mapping", mapping)
    print(f"calibrate_sync_decorated_call_raise: Final candidate SL = {candidate}")
    return candidate


# --------------------------
# Calibration functions for asynchronous variants
# --------------------------
async def calibrate_async_call(handler: ListHandler) -> int:
    expected = "calibrate_async_call"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()
        res, exc = await tracer.Async.call(async_success, 2, 3, stacklevel=sl)
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_async_call mapping", mapping)
    print(f"calibrate_async_call: Final candidate SL = {candidate}")
    return candidate


async def calibrate_async_call_raise(handler: ListHandler) -> int:
    expected = "calibrate_async_call_raise"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()
        try:
            res = await tracer.Async.call_raise(async_success, 2, 3, stacklevel=sl)
        except Exception:
            pass
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_async_call_raise mapping", mapping)
    print(f"calibrate_async_call_raise: Final candidate SL = {candidate}")
    return candidate


async def calibrate_async_decorated_call(handler: ListHandler) -> int:
    expected = "calibrate_async_decorated_call"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()

        @tracer.Async.decorator.call(stacklevel=sl)
        async def dummy_decorated() -> int:
            return await async_success(2, 3)

        res, exc = await dummy_decorated()
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_async_decorated_call mapping", mapping)
    print(f"calibrate_async_decorated_call: Final candidate SL = {candidate}")
    return candidate


async def calibrate_async_decorated_call_raise(handler: ListHandler) -> int:
    expected = "calibrate_async_decorated_call_raise"
    mapping = {}
    candidate = None
    for sl in range(MAX_SL):
        handler.records.clear()

        @tracer.Async.decorator.call_raise(stacklevel=sl)
        async def dummy_decorated() -> int:
            return await async_success(2, 3)

        try:
            res = await dummy_decorated()
        except Exception:
            pass
        if handler.records:
            rec = handler.records[-1]
            mapping[sl] = (rec.funcName, os.path.basename(rec.pathname), rec.funcName == expected)
            if rec.funcName == expected:
                candidate = sl
                break
    print_mapping("calibrate_async_decorated_call_raise mapping", mapping)
    print(f"calibrate_async_decorated_call_raise: Final candidate SL = {candidate}")
    return candidate


# --------------------------
# Main
# --------------------------
async def main() -> None:
    print("Stacklevel Calibration (non-pytest)")
    handler = setup_logging()
    # Calibrate synchronous variants:
    sync_call = calibrate_sync_call(handler)
    sync_call_raise = calibrate_sync_call_raise(handler)
    sync_decorated_call = calibrate_sync_decorated_call(handler)
    sync_decorated_call_raise = calibrate_sync_decorated_call_raise(handler)
    # Calibrate asynchronous variants (using asyncio.run):
    async_call = await calibrate_async_call(handler)
    async_call_raise = await calibrate_async_call_raise(handler)
    async_decorated_call = await calibrate_async_decorated_call(handler)
    async_decorated_call_raise = await calibrate_async_decorated_call_raise(handler)
    print("\n=== FINAL RECOMMENDED DEFAULTS ===")
    print(f"DEFAULT_SYNC_CALL_STACKLEVEL              = {sync_call}")
    print(f"DEFAULT_SYNC_CALL_RAISE_STACKLEVEL        = {sync_call_raise}")
    print(f"DEFAULT_SYNC_DECORATOR_CALL_STACKLEVEL      = {sync_decorated_call}")
    print(f"DEFAULT_SYNC_DECORATOR_CALL_RAISE_STACKLEVEL  = {sync_decorated_call_raise}")
    print(f"DEFAULT_ASYNC_CALL_STACKLEVEL               = {async_call}")
    print(f"DEFAULT_ASYNC_CALL_RAISE_STACKLEVEL         = {async_call_raise}")
    print(f"DEFAULT_ASYNC_DECORATOR_CALL_STACKLEVEL       = {async_decorated_call}")
    print(f"DEFAULT_ASYNC_DECORATOR_CALL_RAISE_STACKLEVEL   = {async_decorated_call_raise}")


if __name__ == "__main__":
    asyncio.run(main())
