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

"""Length-prefixed framing utilities for Bundle BLE transports."""

from __future__ import annotations

from collections.abc import Iterable

from bundle.core import data


class FrameCodec(data.Data):
    """Decode arbitrary BLE notification splits using a 2-byte BE header."""

    _buffer: bytearray = data.PrivateAttr(default_factory=bytearray)

    def encode(self, payload: bytes) -> list[bytes]:
        """Wrap *payload* with its length prefix."""

        if len(payload) > 0xFFFF:
            raise ValueError("payload too large for 2-byte length prefix")
        frame = len(payload).to_bytes(2, "big") + payload
        return [frame]

    def feed(self, chunk: bytes) -> Iterable[bytes]:
        """Yield every completed frame extracted from *chunk*."""

        if not chunk:
            return []

        self._buffer.extend(chunk)
        frames: list[bytes] = []
        while True:
            if len(self._buffer) < 2:
                break

            payload_length = int.from_bytes(self._buffer[:2], "big")
            frame_length = 2 + payload_length

            if len(self._buffer) < frame_length:
                break

            frame = bytes(self._buffer[2:frame_length])
            del self._buffer[:frame_length]
            frames.append(frame)

        return frames
