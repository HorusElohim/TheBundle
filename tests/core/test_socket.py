import asyncio
from pathlib import Path
import bundle
import pytest
import zmq

DEFAULT_SAFE_SLEEP = 0.1
PROTOCOLS = ["tcp", "ipc", "inproc"]
HAS_DRAFT_SUPPORT = zmq.has("draft")

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
async def test_pub_sub(protocol, tmp_path):
    """
    Test PUB/SUB pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5555)

    # Create the publisher and subscriber sockets
    async with (
        bundle.core.Socket.pub().bind(endpoint) as publisher,
        bundle.core.Socket.sub().connect(endpoint).subscribe(b"topic") as subscriber,
    ):
        # Allow some time for the subscriber to connect and subscribe
        # This is crucial to ensure the subscriber is ready to receive messages
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Send a message from the publisher
        message = b"topic Hello, Subscribers!"
        await publisher.send(message)

        # Receive the message on the subscriber
        received = await subscriber.recv()

        # Verify that the received message matches the sent message
        assert received == message

    return f"Socket-PubSub-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
async def test_push_pull(protocol, tmp_path):
    """
    Test PUSH/PULL pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5556)

    # Create the pusher and puller sockets
    async with (
        bundle.core.Socket.push().bind(endpoint) as pusher,
        bundle.core.Socket.pull().connect(endpoint) as puller,
    ):
        # Allow some time for the puller to connect
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Send a message from the pusher
        message = b"Task 1"
        await pusher.send(message)

        # Receive the message on the puller
        received = await puller.recv()

        # Verify that the received message matches the sent message
        assert received == message

    return f"Socket-PushPull-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
async def test_req_rep(protocol, tmp_path):
    """
    Test REQ/REP pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5557)

    # Create the requester and replier sockets
    async with (
        bundle.core.Socket.req().connect(endpoint) as requester,
        bundle.core.Socket.rep().bind(endpoint) as replier,
    ):
        # Allow some time for the connection to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Send request and receive reply
        request = b"Hello, REP!"
        reply = b"Hello, REQ!"

        # Requester sends a request
        await requester.send(request)

        # Replier receives the request
        received_request = await replier.recv()
        assert received_request == request

        # Replier sends a reply
        await replier.send(reply)

        # Requester receives the reply
        received_reply = await requester.recv()
        assert received_reply == reply

    return f"Socket-ReqRep-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
async def test_dealer_router(protocol, tmp_path):
    """
    Test DEALER/ROUTER pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5558)

    # Create the DEALER and ROUTER sockets
    async with (
        bundle.core.Socket.dealer().connect(endpoint) as dealer,
        bundle.core.Socket.router().bind(endpoint) as router,
    ):
        # Allow some time for the connection to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Dealer sends message to Router
        message_to_router = b"Hello, Router!"
        await dealer.send(message_to_router)

        # Router receives the message
        router_parts = await router.recv_multipart()
        assert len(router_parts) >= 2  # Identity, content
        identity, content = router_parts[0], router_parts[1]
        assert content == message_to_router

        # Router sends reply to Dealer
        reply_to_dealer = b"Hello, Dealer!"
        await router.send_multipart([identity, reply_to_dealer])

        # Dealer receives the reply
        received_reply = await dealer.recv()
        assert received_reply == reply_to_dealer

    return f"Socket-DealerRouter-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
async def test_proxy(protocol, tmp_path):
    """
    Test Proxy functionality with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    frontend_endpoint = resolve_endpoint(protocol, tmp_path / "frontend", 5559)
    backend_endpoint = resolve_endpoint(protocol, tmp_path / "backend", 5560)

    # Create the sockets
    async with (
        # Frontend socket (SUB socket) binds to frontend endpoint
        bundle.core.Socket.sub().bind(frontend_endpoint).subscribe(b"") as frontend,
        # Backend socket (PUB socket) binds to backend endpoint
        bundle.core.Socket.pub().bind(backend_endpoint) as backend,
        # Publisher connects to the frontend endpoint
        bundle.core.Socket.pub().connect(frontend_endpoint) as publisher,
        # Subscriber connects to the backend endpoint
        bundle.core.Socket.sub().connect(backend_endpoint).subscribe(b"") as subscriber,
    ):
        # Start the proxy in a separate task
        proxy_task = asyncio.create_task(bundle.core.Socket.proxy(frontend, backend))

        # Allow the proxy task to initialize and connections to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Publisher sends message
        message = b"Proxy Test Message"
        await publisher.send(message)

        # Subscriber receives the proxied message
        try:
            # Use a timeout to prevent the test from hanging
            received = await asyncio.wait_for(subscriber.recv(), timeout=1.0)
            assert received == message
        finally:
            # Cancel the proxy task
            proxy_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await proxy_task

    return f"Socket-Proxy-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
async def test_pair(protocol, tmp_path):
    """
    Test PAIR pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5561)

    # Create the PAIR sockets
    async with (
        bundle.core.Socket.pair().bind(endpoint) as socket_a,
        bundle.core.Socket.pair().connect(endpoint) as socket_b,
    ):
        # Allow some time for the connection to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Socket A sends a message to Socket B
        message = b"Hello, PAIR!"
        await socket_a.send(message)

        # Socket B receives the message
        received = await socket_b.recv()
        assert received == message

        # Socket B sends a reply back to Socket A
        reply = b"Hello, back!"
        await socket_b.send(reply)

        # Socket A receives the reply
        received_reply = await socket_a.recv()
        assert received_reply == reply

    return f"Socket-Pair-{protocol.upper()}"


# Now, adding tests for the missing SocketTypes


@bundle_cprofile
@parametrize_socket_protocol
async def test_xpub_xsub(protocol, tmp_path):
    """
    Test XPUB/XSUB pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5562)

    # Create the XPUB and XSUB sockets
    async with (
        bundle.core.Socket.xpub().bind(endpoint) as xpublisher,
        bundle.core.Socket.xsub().connect(endpoint) as xsubscriber,
    ):
        # Allow some time for the connection to establish
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # XSUB subscribes to all topics by sending a subscription message
        await xsubscriber.send(b"\x01")  # Subscribe to all topics

        # XPUB receives the subscription message
        subscription = await xpublisher.recv()
        assert subscription == b"\x01"  # Subscription message

        # XPUB sends a message
        message = b"topic Hello, XSUB Subscribers!"
        await xpublisher.send(message)

        # XSUB receives the message
        received = await xsubscriber.recv()
        assert received == message

    return f"Socket-XPubXSub-{protocol.upper()}"


@bundle_cprofile
async def test_stream():
    """
    Basic Functionality Test for STREAM bundle.core.socket.

    Verifies that a ZeroMQ STREAM server can communicate with a standard TCP client.

    Steps:
    1. The STREAM server binds to a TCP endpoint.
    2. A standard TCP client connects to the server.
    3. The client sends a message to the server.
    4. The server receives an initial empty message indicating a new connection.
    5. The server receives the actual message from the client.
    6. The server sends a reply back to the client using the connection identity.
    7. The client receives the reply.
    8. Verify that the received messages match the sent messages.
    9. Close the client connection gracefully.

    Tips:
    - Use the identity frame provided by the STREAM socket to route messages back to the correct client.
    - Be aware that the initial empty message signifies a new connection.
    - When sending data to the client, include the identity frame followed by the data.

    """
    port = 5563
    host = "127.0.0.1"
    endpoint = f"tcp://{host}:{port}"

    # Create the STREAM server socket
    async with bundle.core.Socket.stream().bind(endpoint) as server:
        # Allow some time for the server to start
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)

        # Use a standard TCP client
        reader, writer = await asyncio.open_connection(host, port)

        # Client sends message to server
        message = b"Hello, STREAM Server!"
        writer.write(message)
        await writer.drain()

        # Server receives initial connection notification (empty message)
        initial_parts = await server.recv_multipart()
        assert len(initial_parts) == 2  # [identity, empty message]
        identity, empty_message = initial_parts
        assert empty_message == b""  # Initial empty message indicating new connection

        # Server receives the actual message
        message_parts = await server.recv_multipart()
        assert len(message_parts) == 2  # [identity, message]
        identity2, message_received = message_parts
        assert identity2 == identity  # Identity should be the same
        assert message_received == message

        # Server sends reply to client
        reply = b"Hello, STREAM Client!"
        await server.send_multipart([identity, reply])

        # Client receives the reply
        data = await reader.read(1024)
        assert data == reply

        # Close the client connection
        writer.close()
        await writer.wait_closed()

    return "Socket-Stream"


@bundle_cprofile
@parametrize_socket_protocol
@pytest.mark.skipif(not HAS_DRAFT_SUPPORT, reason="DRAFT support is not enabled in pyzmq/libzmq")
async def test_server_client(protocol, tmp_path):
    """
    Test SERVER/CLIENT pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5564)

    async with (
        bundle.core.Socket.server().bind(endpoint) as server,
        bundle.core.Socket.client().connect(endpoint) as client,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)
        # Client sends request to Server
        await client.send(b"Hello, SERVER!")

        # Server receives the request
        request = await server.recv()
        assert request == b"Hello, SERVER!"

        # Server sends reply to Client
        await server.send(b"Hello, CLIENT!")

        # Client receives the reply
        reply = await client.recv()
        assert reply == b"Hello, CLIENT!"

    return f"Socket-ServerClient-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
@pytest.mark.skipif(not HAS_DRAFT_SUPPORT, reason="DRAFT support is not enabled in pyzmq/libzmq")
async def test_radio_dish(protocol, tmp_path):
    """
    Test RADIO/DISH pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5565)

    async with (
        bundle.core.Socket.radio().bind(endpoint) as radio,
        bundle.core.Socket.dish().connect(endpoint).subscribe(b"topic") as dish,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)
        # Radio sends message
        message = b"topic Hello, DISH!"
        await radio.send(message)

        # Dish receives message
        received = await dish.recv()
        assert received == message

    return f"Socket-RadioDish-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
@pytest.mark.skipif(not HAS_DRAFT_SUPPORT, reason="DRAFT support is not enabled in pyzmq/libzmq")
async def test_gather_scatter(protocol, tmp_path):
    """
    Test GATHER/SCATTER pattern with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5566)

    async with (
        bundle.core.Socket.scatter().bind(endpoint) as scatter,
        bundle.core.Socket.gather().connect(endpoint) as gatherer,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)
        # Scatter sends message
        message = b"Hello, GATHER!"
        await scatter.send(message)

        # Gatherer receives message
        received = await gatherer.recv()
        assert received == message

    return f"Socket-GatherScatter-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
@pytest.mark.skipif(not HAS_DRAFT_SUPPORT, reason="DRAFT support is not enabled in pyzmq/libzmq")
async def test_peer(protocol, tmp_path):
    """
    Test PEER socket with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5567)

    async with (
        bundle.core.Socket.peer().bind(endpoint) as peer_a,
        bundle.core.Socket.peer().connect(endpoint) as peer_b,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)
        # Peer A sends message to Peer B
        await peer_a.send(b"Hello from Peer A")
        received = await peer_b.recv()
        assert received == b"Hello from Peer A"

        # Peer B sends message to Peer A
        await peer_b.send(b"Hello from Peer B")
        received = await peer_a.recv()
        assert received == b"Hello from Peer B"

    return f"Socket-Peer-{protocol.upper()}"


@bundle_cprofile
@parametrize_socket_protocol
@pytest.mark.skipif(not HAS_DRAFT_SUPPORT, reason="DRAFT support is not enabled in pyzmq/libzmq")
async def test_channel(protocol, tmp_path):
    """
    Test CHANNEL socket with parameterized protocols.
    """
    if bundle.core.platform_info.is_windows and protocol == "ipc":
        pytest.skip("Skipping IPC tests on Windows.")

    endpoint = resolve_endpoint(protocol, tmp_path, 5568)

    async with (
        bundle.core.Socket.channel().bind(endpoint) as channel_server,
        bundle.core.Socket.channel().connect(endpoint) as channel_client,
    ):
        await asyncio.sleep(DEFAULT_SAFE_SLEEP)
        # Channel client sends message
        await channel_client.send(b"Hello, CHANNEL Server!")
        received = await channel_server.recv()
        assert received == b"Hello, CHANNEL Server!"

        # Channel server sends reply
        await channel_server.send(b"Hello, CHANNEL Client!")
        reply = await channel_client.recv()
        assert reply == b"Hello, CHANNEL Client!"

    return f"Socket-Channel-{protocol.upper()}"
