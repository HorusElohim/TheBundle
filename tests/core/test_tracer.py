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
