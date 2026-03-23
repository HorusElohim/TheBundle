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

"""Bundle BLE module public interface definitions."""

from __future__ import annotations

from .device import Advertisement, Device
from .framing import FrameCodec
from .link import NordicLink
from .manager import Manager
from .scanner import DEFAULT_SCAN_TIMEOUT, Scanner, ScanResult

__all__ = [
    "DEFAULT_SCAN_TIMEOUT",
    "Advertisement",
    "Device",
    "FrameCodec",
    "Manager",
    "NordicLink",
    "ScanResult",
    "Scanner",
]
