import asyncio
import hashlib
from pathlib import Path

import pytest

import bundle
from bundle.chat import PeerFileMessage, PeerMessageType, PeerNode, PeerTextMessage

DEFAULT_SAFE_SLEEP = 0.1
PROTOCOLS = ["tcp", "ipc", "inproc"]

# Mark all tests in this module as asynchronous
pytestmark = pytest.mark.asyncio

parametrize_socket_protocol = pytest.mark.parametrize("protocol", PROTOCOLS)
bundle_cprofile = pytest.mark.bundle_cprofile(
    expected_duration=300_000_000, performance_threshold=100_000_000
)  # 300ms + ~100ms


def resolve_endpoint(protocol: str, tmp_path: Path, port: int):
    match protocol:
        case "tcp":
            return f"{protocol}://127.0.0.1:{port}"
        case "inproc":
            tmp_path = bundle.core.utils.ensure_path(tmp_path)
            return f"{protocol}://{str(tmp_path / 'sock.sock')}"
        case "ipc":
            # IPC has a maximum of 103 characters
            tmp_path = bundle.core.utils.ensure_path(Path("/tmp/") / tmp_path.name)
            return f"{protocol}://{str(tmp_path / 'sock.sock')}"

    raise ValueError(f"Unsupported protocol {protocol}")


@bundle_cprofile
@parametrize_socket_protocol
async def test_chat_text(tmp_path: Path, protocol: str):
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 7777)

    async with (
        PeerNode(endpoint=endpoint).bind() as server,
        PeerNode(endpoint=endpoint).connect() as client,
    ):
        # Allow time for connection to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        received_by_client: list[PeerTextMessage] = []
        received_by_server: list[PeerTextMessage] = []

        async def on_server_text(msg: PeerTextMessage):
            received_by_server.append(msg)
            await server.send(
                PeerTextMessage(
                    sender="server",
                    recipient=msg.sender,
                    content=f"Echo: {msg.content}",
                )
            )

        async def on_client_text(msg: PeerTextMessage):
            received_by_client.append(msg)

        server.on(PeerMessageType.TEXT, on_server_text)
        client.on(PeerMessageType.TEXT, on_client_text)

        # Process one message on server then one on client

        sent_msg = PeerTextMessage(sender="test-client", content="hello!")

        # Extra readiness window similar to core socket tests
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        await client.send(sent_msg)
        await asyncio.wait_for(server.receive(), timeout=2.0)
        await asyncio.wait_for(client.receive(), timeout=2.0)

        assert received_by_client and received_by_client[0].content == f"Echo: {sent_msg.content}"
        assert received_by_client[0].sender == "server"
        assert received_by_server and received_by_server[0].content == sent_msg.content
        assert received_by_server[0].sender == sent_msg.sender
        assert received_by_server[0].recipient == ""
        # Ensure no extra messages
        assert len(received_by_client) == 1
        assert len(received_by_server) == 1


@bundle_cprofile
@parametrize_socket_protocol
async def test_chat_file(tmp_path: Path, protocol: str):
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 8888)

    # Prepare a small binary file
    original = b"\x00\x01\x02Hello\xffBinary\x10Data"
    original_sha = hashlib.sha256(original).hexdigest()

    async with (
        PeerNode(endpoint=endpoint).bind() as server,
        PeerNode(endpoint=endpoint).connect() as client,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        received_files: list[PeerFileMessage] = []

        async def on_server_file(msg: PeerFileMessage):
            received_files.append(msg)

        server.on(PeerMessageType.FILE, on_server_file)

        msg = PeerFileMessage(sender="tester", filename="sample.bin", filedata=original)
        await client.send(msg)

        await asyncio.wait_for(server.receive(), timeout=2.0)

        assert received_files, "Server did not receive file message"
        got = received_files[0]
        assert got.filename == "sample.bin"
        assert got.filedata == original
        assert hashlib.sha256(got.filedata).hexdigest() == original_sha
