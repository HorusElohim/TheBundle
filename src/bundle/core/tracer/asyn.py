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
from typing import Callable, TypeVar, ParamSpec, Awaitable, cast

from .common import log_call_success, log_call_exception, log_cancelled_exception

P = ParamSpec("P")
R = TypeVar("R")


async def call(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
    *args: P.args,
    stacklevel: int = 3,  # type: ignore
    **kwargs: P.kwargs,
) -> tuple[R | None, BaseException | None]:
    try:
        result = await (
            asyncio.to_thread(func, *args, **kwargs) if not asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        )
        log_call_success(func, args, kwargs, result, stacklevel)
        return cast(R, result), None
    except asyncio.CancelledError as cancel_exception:
        log_cancelled_exception(func, args, kwargs, cancel_exception, stacklevel)
        return None, cancel_exception
    except Exception as exception:
        log_call_exception(func, args, kwargs, exception, stacklevel)
        return None, exception


async def call_raise(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
    *args: P.args,
    stacklevel: int = 4,  # type: ignore
    **kwargs: P.kwargs,
) -> R:
    result, error = await call(func, *args, stacklevel=stacklevel, **kwargs)
    if error:
        raise error
    return cast(R, result)


def decorator_call(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[tuple[R | None, BaseException | None]]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R | None, BaseException | None]:
        return await call(func, *args, **kwargs, stacklevel=5)

    return wrapper


def decorator_call_raise(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await call_raise(func, *args, **kwargs, stacklevel=5)

    return wrapper
