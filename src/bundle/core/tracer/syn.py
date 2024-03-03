from functools import wraps
from typing import Callable, TypeVar, Concatenate, ParamSpec

from .common import log_call_success, log_call_exception


P, R = ParamSpec("P"), TypeVar("R")


def call(
    func: Callable[Concatenate[P], R], *args: P.args, stacklevel: int = 3, **kwargs: P.kwargs
) -> tuple[R | None, Exception | None]:
    result: None | R = None
    try:
        result = func(*args, **kwargs)
        log_call_success(func, args, kwargs, result, stacklevel)
    except Exception as exception:
        log_call_exception(func, args, kwargs, exception, stacklevel)
        return None, exception

    return result, None


def call_raise(func: Callable[Concatenate[P], R], *args: P.args, stacklevel: int = 3, **kwargs: P.kwargs) -> R:
    result, exception = call(func, *args, stacklevel=stacklevel, **kwargs)
    if exception:
        raise exception
    return result


def decorator_call(func: Callable[P, R]) -> Callable[P, tuple[R | None, Exception | None]]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, Exception | None]:
        return call(func, *args, **kwargs, stacklevel=5)

    return wrapper


def decorator_call_raise(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return call_raise(func, *args, **kwargs, stacklevel=5)

    return wrapper
