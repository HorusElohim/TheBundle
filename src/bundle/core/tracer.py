# Copyright 2025 HorusElohim
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
import sys
import asyncio
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    ParamSpec,
    TypeVar,
    cast,
)
from . import logger

P = ParamSpec("P")
R = TypeVar("R")

log = logger.get_logger(__name__)

DEFAULT_LOG_LEVEL = logger.Level.DEBUG
DEFAULT_LOG_EXC_LEVEL = logger.Level.ERROR

# Conditionally adjusting the stacklevel.
# The following stacklevel constants are tuned based on the Python version.
# In Python versions earlier than 3.11, the call stack tends to have fewer frames when logging,
# so a lower stacklevel is sufficient to capture the correct external caller.
#
# Starting with Python 3.11 (and some changes seen in Python 3.10), internal wrappers and changes
# in the logging module and async frameworks introduce extra frames. This causes the default stacklevel
# value used by the logging methods to point to an internal module (like pytest's or asyncio's modules)
# instead of the expected caller.
if sys.version_info < (3, 11):
    DEFAULT_SYNC_CALL_STACKLEVEL = 2
    DEFAULT_SYNC_CALL_RAISE_STACKLEVEL = 3
    DEFAULT_SYNC_DECORATOR_CALL_STACKLEVEL = 3
    DEFAULT_SYNC_DECORATOR_CALL_RAISE_STACKLEVEL = 4
    DEFAULT_ASYNC_CALL_STACKLEVEL = 2
    DEFAULT_ASYNC_CALL_RAISE_STACKLEVEL = 3
    DEFAULT_ASYNC_DECORATOR_CALL_STACKLEVEL = 3
    DEFAULT_ASYNC_DECORATOR_CALL_RAISE_STACKLEVEL = 4
else:
    DEFAULT_SYNC_CALL_STACKLEVEL = 3
    DEFAULT_SYNC_CALL_RAISE_STACKLEVEL = 4
    DEFAULT_SYNC_DECORATOR_CALL_STACKLEVEL = 4
    DEFAULT_SYNC_DECORATOR_CALL_RAISE_STACKLEVEL = 5
    DEFAULT_ASYNC_CALL_STACKLEVEL = 3
    DEFAULT_ASYNC_CALL_RAISE_STACKLEVEL = 4
    DEFAULT_ASYNC_DECORATOR_CALL_STACKLEVEL = 4
    DEFAULT_ASYNC_DECORATOR_CALL_RAISE_STACKLEVEL = 5


# --- Synchronous Implementation ---
class Sync:
    @staticmethod
    def call(
        func: Callable[P, R] | Callable[P, Awaitable[R]],
        *args: P.args,
        stacklevel: int = DEFAULT_SYNC_CALL_STACKLEVEL,  # type: ignore
        log_level: logger.Level | None = None,  # type: ignore
        exc_log_level: logger.Level | None = None,  # type: ignore
        **kwargs: P.kwargs,
    ) -> tuple[R | None, Exception | None]:
        result: R | None = None

        log_level = log_level or DEFAULT_LOG_LEVEL
        exc_log_level = exc_log_level or DEFAULT_LOG_EXC_LEVEL

        try:
            if asyncio.iscoroutinefunction(func):
                result = asyncio.run(cast(Coroutine[Any, Any, R], func(*args, **kwargs)))
            else:
                result = cast(R, func(*args, **kwargs))
            log.callable_success(func, args, kwargs, result, stacklevel, log_level)
        except Exception as exception:
            if isinstance(exception, asyncio.CancelledError):
                log.callable_exception(func, args, kwargs, exception, stacklevel, exc_log_level)
            else:
                log.callable_cancel(func, args, kwargs, exception, stacklevel, exc_log_level)
            return None, exception

        return result, None

    @staticmethod
    def call_raise(
        func: Callable[P, R] | Callable[P, Awaitable[R]],
        *args: P.args,
        stacklevel: int = DEFAULT_SYNC_CALL_RAISE_STACKLEVEL,  # type: ignore
        log_level: logger.Level | None = None,  # type: ignore
        exc_log_level: logger.Level | None = None,  # type: ignore
        **kwargs: P.kwargs,
    ) -> R:
        result, exception = Sync.call(
            func, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
        )
        if exception is not None:
            raise exception
        return cast(R, result)

    class decorator:
        @staticmethod
        def call(
            func: Callable[P, R] | Callable[P, Awaitable[R]] | None = None,
            *,
            stacklevel: int = DEFAULT_SYNC_DECORATOR_CALL_STACKLEVEL,
            log_level: logger.Level | None = None,
            exc_log_level: logger.Level | None = None,
        ) -> Callable[P, tuple[R | None, Exception | None]]:
            """
            Decorator that wraps a synchronous callable to log its outcome.
            Returns a tuple (result, exception). Can be used with or without parameters.
            """

            def actual_decorator(
                f: Callable[P, R] | Callable[P, Awaitable[R]],
            ) -> Callable[P, tuple[R | None, Exception | None]]:
                @wraps(f)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, Exception | None]:
                    return Sync.call(
                        f, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
                    )

                return wrapper

            return cast(
                Callable[P, tuple[R | None, Exception | None]],
                actual_decorator if func is None else actual_decorator(func),
            )

        @staticmethod
        def call_raise(
            func: Callable[P, R] | Callable[P, Awaitable[R]] | None = None,
            *,
            stacklevel: int = DEFAULT_SYNC_DECORATOR_CALL_RAISE_STACKLEVEL,
            log_level: logger.Level | None = None,
            exc_log_level: logger.Level | None = None,
        ) -> Callable[P, R]:
            """
            Decorator that wraps a synchronous callable to log its outcome.
            Returns the result directly or raises the logged exception.
            Can be used with or without parameters.
            """

            def actual_decorator(f: Callable[P, R] | Callable[P, Awaitable[R]]) -> Callable[P, R]:
                @wraps(f)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    return Sync.call_raise(
                        f, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
                    )

                return wrapper

            return cast(Callable[P, R], actual_decorator if func is None else actual_decorator(func))


# --- Asynchronous Implementation ---
class Async:
    @staticmethod
    async def call(
        func: Callable[P, R] | Callable[P, Awaitable[R]],
        *args: P.args,
        stacklevel: int = DEFAULT_ASYNC_CALL_STACKLEVEL,  # type: ignore
        log_level: logger.Level | None = None,  # type: ignore
        exc_log_level: logger.Level | None = None,  # type: ignore
        **kwargs: P.kwargs,
    ) -> tuple[R | None, BaseException | None]:
        log_level = log_level if log_level else DEFAULT_LOG_LEVEL
        exc_log_level = exc_log_level if exc_log_level else DEFAULT_LOG_EXC_LEVEL

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(func, *args, **kwargs)
            log.callable_success(func, args, kwargs, result, stacklevel, log_level)
            return cast(R, result), None
        except asyncio.CancelledError as cancel_exception:
            log.callable_exception(func, args, kwargs, cancel_exception, stacklevel, exc_log_level)
            return None, cancel_exception
        except Exception as exception:
            log.callable_cancel(func, args, kwargs, exception, stacklevel, exc_log_level)
            return None, exception

    @staticmethod
    async def call_raise(
        func: Callable[P, R] | Callable[P, Awaitable[R]],
        *args: P.args,
        stacklevel: int = DEFAULT_ASYNC_CALL_RAISE_STACKLEVEL,  # type: ignore
        log_level: logger.Level | None = None,  # type: ignore
        exc_log_level: logger.Level | None = None,  # type: ignore
        **kwargs: P.kwargs,
    ) -> R:
        result, exception = await Async.call(
            func, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
        )
        if exception is not None:
            raise exception
        return cast(R, result)

    class decorator:
        @staticmethod
        def call(
            func: Callable[P, R] | Callable[P, Awaitable[R]] | None = None,
            *,
            stacklevel: int = DEFAULT_ASYNC_DECORATOR_CALL_STACKLEVEL,  # type: ignore
            log_level: logger.Level | None = None,  # type: ignore
            exc_log_level: logger.Level | None = None,  # type: ignore
        ) -> Callable[P, Awaitable[tuple[R | None, BaseException | None]]]:
            """
            Decorator that wraps an asynchronous callable to log its outcome.
            Returns a tuple (result, exception). Can be used with or without parameters.
            """

            def actual_decorator(
                f: Callable[P, R] | Callable[P, Awaitable[R]],
            ) -> Callable[P, Awaitable[tuple[R | None, BaseException | None]]]:
                @wraps(f)
                async def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, BaseException | None]:
                    return await Async.call(
                        f, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
                    )

                return wrapper

            return cast(
                Callable[P, Awaitable[tuple[R | None, BaseException | None]]],
                actual_decorator if func is None else actual_decorator(func),
            )

        @staticmethod
        def call_raise(
            func: Callable[P, R] | Callable[P, Awaitable[R]] | None = None,
            *,
            stacklevel: int = DEFAULT_ASYNC_DECORATOR_CALL_RAISE_STACKLEVEL,  # type: ignore
            log_level: logger.Level | None = None,  # type: ignore
            exc_log_level: logger.Level | None = None,  # type: ignore
        ) -> Callable[P, Awaitable[R]]:
            """
            Decorator that wraps an asynchronous callable to log its outcome.
            Returns the result directly or raises the logged exception.
            Can be used with or without parameters.
            """

            def actual_decorator(f: Callable[P, R] | Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
                @wraps(f)
                async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    return await Async.call_raise(
                        f, *args, stacklevel=stacklevel, log_level=log_level, exc_log_level=exc_log_level, **kwargs
                    )

                return wrapper

            return cast(
                Callable[P, Awaitable[R]],
                actual_decorator if func is None else actual_decorator(func),
            )
