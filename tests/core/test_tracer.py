from __future__ import annotations

import pytest
import logging
import os
from typing import Generator, Any

import pytest
from bundle.core import tracer

# --- Helper functions for testing ---


# Synchronous functions
def sync_success(x: int, y: int) -> int:
    return x + y


def sync_fail(x: int, y: int) -> int:
    raise ValueError("sync error")


# Asynchronous functions
async def async_success(x: int, y: int) -> int:
    return x * y


async def async_fail(x: int, y: int) -> int:
    raise RuntimeError("async error")


# --- Tests for the Synchronous Implementation (Sync) ---


def test_sync_call_with_sync_function():
    result, exc = tracer.Sync.call(sync_success, 2, 3)
    assert result == 5
    assert exc is None


def test_sync_call_with_async_function():
    result, exc = tracer.Sync.call(async_success, 2, 3)
    assert result == 6
    assert exc is None


def test_sync_call_with_sync_exception():
    result, exc = tracer.Sync.call(sync_fail, 2, 3)
    print(exc)
    assert result is None
    assert isinstance(exc, ValueError)
    assert str(exc) == "sync error"


def test_sync_call_with_async_exception():
    result, exc = tracer.Sync.call(async_fail, 2, 3)
    assert result is None
    assert isinstance(exc, RuntimeError)
    assert str(exc) == "async error"


def test_sync_call_raise_with_sync_function():
    result = tracer.Sync.call_raise(sync_success, 2, 3)
    assert result == 5


def test_sync_call_raise_with_async_function():
    result = tracer.Sync.call_raise(async_success, 2, 3)
    assert result == 6


def test_sync_call_raise_with_sync_exception():
    with pytest.raises(ValueError, match="sync error"):
        tracer.Sync.call_raise(sync_fail, 2, 3)


def test_sync_call_raise_with_async_exception():
    with pytest.raises(RuntimeError, match="async error"):
        tracer.Sync.call_raise(async_fail, 2, 3)


# Decorator tests for Sync


@tracer.Sync.decorator.call
def decorated_sync_success(x: int, y: int) -> int:
    return x - y


@tracer.Sync.decorator.call_raise
def decorated_sync_raise_success(x: int, y: int) -> int:
    return x * 2


@tracer.Sync.decorator.call_raise
def decorated_sync_failure(x: int, y: int) -> int:
    raise KeyError("decorated sync error")


def test_sync_decorator_call_with_sync_function():
    result, exc = decorated_sync_success(5, 3)
    assert result == 2
    assert exc is None


def test_sync_decorator_call_raise_with_sync_function():
    result = decorated_sync_raise_success(4, 2)
    assert result == 8


def test_sync_decorator_call_raise_with_sync_exception():
    with pytest.raises(KeyError, match="decorated sync error"):
        decorated_sync_failure(1, 1)


# --- Tests for the Asynchronous Implementation (Async) ---


@pytest.mark.asyncio
async def test_async_call_with_sync_function():
    result, exc = await tracer.Async.call(sync_success, 2, 3)
    assert result == 5
    assert exc is None


@pytest.mark.asyncio
async def test_async_call_with_async_function():
    result, exc = await tracer.Async.call(async_success, 2, 3)
    assert result == 6
    assert exc is None


@pytest.mark.asyncio
async def test_async_call_with_sync_exception():
    result, exc = await tracer.Async.call(sync_fail, 2, 3)
    assert result is None
    assert isinstance(exc, ValueError)


@pytest.mark.asyncio
async def test_async_call_with_async_exception():
    result, exc = await tracer.Async.call(async_fail, 2, 3)
    assert result is None
    assert isinstance(exc, RuntimeError)


@pytest.mark.asyncio
async def test_async_call_raise_with_sync_function():
    result = await tracer.Async.call_raise(sync_success, 2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_async_call_raise_with_async_function():
    result = await tracer.Async.call_raise(async_success, 2, 3)
    assert result == 6


@pytest.mark.asyncio
async def test_async_call_raise_with_sync_exception():
    with pytest.raises(ValueError, match="sync error"):
        await tracer.Async.call_raise(sync_fail, 2, 3)


@pytest.mark.asyncio
async def test_async_call_raise_with_async_exception():
    with pytest.raises(RuntimeError, match="async error"):
        await tracer.Async.call_raise(async_fail, 2, 3)


# Decorator tests for Async


@tracer.Async.decorator.call
async def decorated_async_success(x: int, y: int) -> int:
    return x - y


@tracer.Async.decorator.call_raise
async def decorated_async_raise_success(x: int, y: int) -> int:
    return x * 3


@tracer.Async.decorator.call_raise
async def decorated_async_failure(x: int, y: int) -> int:
    raise IndexError("decorated async error")


@pytest.mark.asyncio
async def test_async_decorator_call_with_async_function():
    result, exc = await decorated_async_success(5, 3)
    assert result == 2
    assert exc is None


@pytest.mark.asyncio
async def test_async_decorator_call_raise_with_async_function():
    result = await decorated_async_raise_success(4, 2)
    assert result == 12


@pytest.mark.asyncio
async def test_async_decorator_call_raise_with_async_exception():
    with pytest.raises(IndexError, match="decorated async error"):
        await decorated_async_failure(1, 1)


# A simple logging handler that collects records.
class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def list_handler() -> Generator[Any, Any, ListHandler]:
    handler = ListHandler()
    # Use the logger from your tracer module.
    # Adjust the logger name if necessary.
    tracer.log.addHandler(handler)
    # Set a low log level to capture all records.
    tracer.log.setLevel(logging.DEBUG)
    yield handler
    tracer.log.removeHandler(handler)


@pytest.fixture
def file_name() -> str:
    return os.path.basename(__file__)


def assert_log_correct(record: logging.LogRecord, file_name: str, func_name: str) -> bool:
    # Check that the logged record's pathname ends with our test file name
    # and that the funcName is not one of the known wrappers.
    assert file_name == os.path.basename(record.pathname), f"wrong file_name -> {file_name}"
    return func_name == record.funcName, f"Wrong func_name -> {func_name}"


# --- Direct Calls Tests ---
def test_sync_direct_stacklevel(list_handler: ListHandler, file_name) -> None:
    test_file = os.path.basename(__file__)

    def dummy() -> int:
        return 42

    result, exc = tracer.Sync.call(dummy)
    assert result == 42, "Dummy function did not return expected value"
    assert exc == None
    record = list_handler.records[-1]
    assert_log_correct(record, file_name, "test_sync_direct_stacklevel")


@pytest.mark.asyncio
async def test_async_direct_stacklevel(list_handler: ListHandler, file_name: str) -> None:
    async def dummy_async() -> int:
        return 123

    result, exc = await tracer.Async.call(dummy_async)
    assert result == 123, "Dummy async function did not return expected value"
    assert exc is None
    record = list_handler.records[-1]
    # Expect the external caller to be this test function.
    assert_log_correct(record, file_name, "test_async_direct_stacklevel")


# --- Decorated Calls Tests ---


@tracer.Sync.decorator.call
def dummy_decorated_sync() -> int:
    return 100


def test_sync_decorator_stacklevel(list_handler: ListHandler, file_name: str) -> None:
    result, exc = dummy_decorated_sync()
    assert result == 100, "Decorated sync function did not return expected value"
    assert exc is None
    record = list_handler.records[-1]
    # Expect the external caller to be this test function.
    assert_log_correct(record, file_name, "test_sync_decorator_stacklevel")


@tracer.Async.decorator.call
async def dummy_decorated_async() -> int:
    return 456


@pytest.mark.asyncio
async def test_async_decorator_stacklevel(list_handler: ListHandler, file_name: str) -> None:
    result, exc = await dummy_decorated_async()
    assert result == 456, "Decorated async function did not return expected value"
    assert exc is None
    record = list_handler.records[-1]
    # Expect the external caller to be this test function.
    assert_log_correct(record, file_name, "test_async_decorator_stacklevel")
