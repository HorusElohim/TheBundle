# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import asyncio
from functools import wraps
from typing import Awaitable, Callable, Concatenate, ParamSpec, TypeVar, cast

from .. import logger

P = ParamSpec("P")
R = TypeVar("R")

log = logger.get_logger(__name__)


def call(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
    *args: P.args,
    stacklevel: int = 3,  # type:ignore
    log_level: logger.Level | None = None,
    **kwargs: P.kwargs,
) -> tuple[R | None, Exception | None]:
    result: None | R = None
    try:
        if asyncio.iscoroutinefunction(func):
            stacklevel += 3
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)
        if log_level is None:
            log_level = logger.Level.DEBUG
        log.callable_success(func, args, kwargs, result, stacklevel, log_level)
    except Exception as exception:
        log.callable_exception(func, args, kwargs, exception, stacklevel)
        return None, exception

    return result, None


def call_raise(
    func: Callable[Concatenate[P], R],
    *args: P.args,
    stacklevel: int = 3,  # type:ignore
    log_level: logger.Level | None = None,
    **kwargs: P.kwargs,
) -> R:
    result, exception = call(func, *args, stacklevel=stacklevel, log_level=log_level, **kwargs)
    if exception:
        raise exception
    return cast(R, result)


def decorator_call(
    func: Callable[P, R] | None = None,
    *,
    log_level: logger.Level | None = None,
) -> Callable[..., object]:
    """
    Decorator that wraps a callable to log its outcome.
    Returns a tuple (result, exception).
    Can be used with or without parameters.
    """

    def actual_decorator(f: Callable[P, R]) -> Callable[P, tuple[R | None, Exception | None]]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, Exception | None]:
            return call(f, *args, **kwargs, stacklevel=5, log_level=log_level)

        return wrapper

    if func is None:
        return actual_decorator
    return actual_decorator(func)


def decorator_call_raise(
    func: Callable[P, R] | None = None,
    *,
    log_level: logger.Level | None = None,
) -> R:
    """
    Decorator that wraps a callable to log its outcome.
    Returns the result directly or raises the logged exception.
    Can be used with or without parameters.
    """

    def actual_decorator(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return call_raise(f, *args, **kwargs, stacklevel=5, log_level=log_level)

        return wrapper

    if func is None:
        return actual_decorator
    return actual_decorator(func)
