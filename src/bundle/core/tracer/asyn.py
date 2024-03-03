import asyncio
from functools import wraps
from typing import Callable, TypeVar, Concatenate, ParamSpec, Awaitable

from .common import log_call_success, log_call_exception, log_cancelled_exception

P, R = ParamSpec("P"), TypeVar("R")


async def call(
    func: Callable[Concatenate[P], R] | Callable[Concatenate[P], Awaitable[R]],
    *args: P.args,
    stacklevel=3,
    **kwargs: P.kwargs,
) -> tuple[R | None, Exception | None]:
    result: None | R = None
    try:
        result = await (
            asyncio.to_thread(func, *args, **kwargs) if not asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        )
        log_call_success(func, args, kwargs, result, stacklevel)
    except asyncio.CancelledError as cancel_exception:
        log_cancelled_exception(func, args, kwargs, cancel_exception, stacklevel)
        return None, cancel_exception
    except Exception as exception:
        log_call_exception(func, args, kwargs, exception, stacklevel)
        return None, exception

    return result, None


async def call_raise(
    func: Callable[Concatenate[P], R] | Callable[Concatenate[P], Awaitable[R]],
    *args: P.args,
    stacklevel=4,
    **kwargs: P.kwargs,
) -> R:
    result, has_exception = await call(func, *args, stacklevel=stacklevel, **kwargs)
    if has_exception:
        raise has_exception
    return result


def decorator_call(func: Callable[P, R]) -> Callable[P, Awaitable[tuple[R | None, Exception | None]]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, Exception | None]:
        return await call(func, *args, **kwargs, stacklevel=5)

    return wrapper


def decorator_call_raise(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await call_raise(func, *args, **kwargs, stacklevel=5)

    return wrapper
