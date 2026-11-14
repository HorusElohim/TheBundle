# Copyright 2026 HorusElohim
# Licensed under the Apache License, Version 2.0.
"""Exercise the installed voice dependencies, not a mocked encryption API."""

import json
import struct
from pathlib import Path

import davey
import pytest
from discord.gateway import DiscordVoiceWebSocket
from discord.voice_state import VoiceConnectionState


@pytest.mark.asyncio
async def test_discord_handshake_activates_dave_encryption() -> None:
    """An accepted MLS commit must make outgoing audio E2EE-ready.

    discord.py 2.7.1 accepts davey 0.2 via its dependency metadata, but never
    activates its new transition API. Packets then bypass DAVE and are inaudible.
    Use the real gateway handler and crypto library with upstream public vectors.
    """
    fixture = json.loads((Path(__file__).parent / "fixtures/dave_session.json").read_text())
    session = davey.DaveSession(1, fixture["MY_USER_ID"], fixture["CHANNEL_ID"])
    session.set_external_sender(bytes.fromhex(fixture["EXTERNAL_SENDER"]))
    session.get_serialized_key_package()
    proposal = session.process_proposals(davey.ProposalsOperationType.append, bytes.fromhex(fixture["APPENDING_PROPOSALS"]))
    assert proposal is not None

    # No network/socket is needed to process an initial (transition 0) commit.
    state = object.__new__(VoiceConnectionState)
    state.dave_session = session
    state.dave_protocol_version = 1
    gateway = object.__new__(DiscordVoiceWebSocket)
    gateway._connection = state
    frame = struct.pack(">HBH", 1, gateway.MLS_ANNOUNCE_COMMIT_TRANSITION, 0) + proposal.commit
    await gateway.received_binary_message(frame)

    assert state.can_encrypt, "MLS accepted but voice packets would bypass DAVE encryption"
    opus_frame = b"\xfc\xff\xfe"  # Non-silence Opus payload: silence is deliberately passed through.
    encrypted = session.encrypt_opus(opus_frame)
    assert encrypted != opus_frame
    assert len(encrypted) > len(opus_frame)
