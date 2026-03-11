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
