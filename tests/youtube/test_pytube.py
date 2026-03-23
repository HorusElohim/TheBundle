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

import pytest

from bundle.youtube.pytube import _stream_option


class _FakeStream:
    itag = 18
    url = "https://example.invalid/video.mp4"
    resolution = "360p"
    abr = ""
    fps = 30
    mime_type = "video/mp4"
    progressive = True
    filesize = 1234


class _BrokenUrlStream(_FakeStream):
    @property
    def url(self):
        raise RuntimeError("url not available")


@pytest.mark.asyncio
async def test_stream_option_includes_url():
    option = await _stream_option(_FakeStream(), "video")
    assert option.url == "https://example.invalid/video.mp4"
    assert option.itag == 18
    assert option.progressive is True


@pytest.mark.asyncio
async def test_stream_option_handles_unavailable_url():
    option = await _stream_option(_BrokenUrlStream(), "video")
    assert option.url == ""
