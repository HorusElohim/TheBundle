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

from .. import logger
from typing import TypeVar, ParamSpec

log = logger.get_logger(__name__)

P, R = ParamSpec("P"), TypeVar("R")


def get_callable_name(callable_obj):
    """
    Helper function to retrieve the name of a callable for logging purposes.

    Args:
        callable_obj: The callable object whose name is to be retrieved.

    Returns:
        str: The qualified name of the callable.
    """
    if hasattr(callable_obj, "__qualname__"):
        return callable_obj.__qualname__
    elif hasattr(callable_obj, "__class__") and hasattr(callable_obj.__class__, "__qualname__"):
        return callable_obj.__class__.__qualname__
    elif hasattr(callable_obj, "__call__") and hasattr(callable_obj.__call__, "__qualname__"):
        return callable_obj.__call__.__qualname__
    return str(callable_obj)


def log_call_success(func, args, kwargs, result, stacklevel):
    log.debug(
        "%s  %s.%s(%s, %s) -> %s",
        log.Emoji.success,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        result,
        stacklevel=stacklevel,
    )


def log_call_exception(func, args, kwargs, exception, stacklevel):
    log.error(
        "%s  %s.%s(%s, %s). Exception: %s",
        log.Emoji.failed,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        exception,
        exc_info=True,
        stacklevel=stacklevel,
    )


def log_cancelled_exception(func, args, kwargs, exception, stacklevel):
    log.warning(
        "%s  %s.%s(%s, %s) -> async cancel exception: %s",
        logger.Emoji.warning,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        exception,
        exc_info=False,
        stacklevel=stacklevel - 1,
    )
