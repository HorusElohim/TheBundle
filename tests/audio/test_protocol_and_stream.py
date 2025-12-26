from pathlib import Path
from typing import Any

import numpy as np
import pytest

from bundle.audio.protocol import PROTOCOL_VERSION, AudioMessageType, build_envelope
from bundle.website.sections.audio import stream


def _write_wav(path: Path, sample_rate: int, samples: np.ndarray) -> None:
    import wave

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype(np.int16).tobytes())


class DummyWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


@pytest.fixture()
def audio_stream() -> tuple[stream.AudioStream, DummyWebSocket]:
    ws = DummyWebSocket()
    return stream.AudioStream(ws), ws


@pytest.fixture()
def short_wav(tmp_path: Path) -> Path:
    sample_rate = 2000
    samples = np.arange(int(sample_rate * 0.2), dtype=np.int16)
    wav_path = tmp_path / "short.wav"
    _write_wav(wav_path, sample_rate, samples)
    return wav_path


@pytest.mark.asyncio
async def test_handle_message_rejects_wrong_version(audio_stream):
    audio_stream, ws = audio_stream

    await audio_stream.handle_message({"v": PROTOCOL_VERSION + 1, "type": AudioMessageType.LOAD, "payload": {}})

    assert ws.sent[0]["type"] == AudioMessageType.ERROR.value


@pytest.mark.asyncio
async def test_handle_load_and_view_updates(audio_stream, short_wav: Path):
    audio_stream, ws = audio_stream

    await audio_stream.handle_message(
        {"v": PROTOCOL_VERSION, "type": AudioMessageType.LOAD, "payload": {"path": str(short_wav)}}
    )

    assert any(msg["type"] == AudioMessageType.STATE.value for msg in ws.sent)
    assert any(msg["type"] == AudioMessageType.WAVEFORM_CHUNK.value for msg in ws.sent)

    await audio_stream.handle_message(
        {
            "v": PROTOCOL_VERSION,
            "type": AudioMessageType.VIEW_SET,
            "payload": {"zoom": 4.0, "offset_sec": 0.05},
        }
    )

    last_state = next(msg for msg in reversed(ws.sent) if msg["type"] == AudioMessageType.STATE.value)
    assert last_state["payload"]["view"]["zoom"] == 4.0


@pytest.mark.asyncio
async def test_handle_missing_path_returns_error(audio_stream):
    audio_stream, ws = audio_stream

    await audio_stream.handle_message({"v": PROTOCOL_VERSION, "type": AudioMessageType.LOAD, "payload": {}})

    assert ws.sent[-1]["type"] == AudioMessageType.ERROR.value


def test_build_envelope_sets_version():
    envelope = build_envelope("x", {"foo": "bar"})
    assert envelope["v"] == PROTOCOL_VERSION
    assert envelope["type"] == "x"
    assert envelope["payload"] == {"foo": "bar"}
