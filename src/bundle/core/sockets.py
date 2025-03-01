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

from __future__ import annotations

import asyncio
from enum import IntEnum
from typing import ClassVar, Generic, Type, TypeVar

import zmq
import zmq.asyncio

from . import data, entity, tracer
from .logger import get_logger

logger = get_logger(__name__)


DRAFT_SOCKET_TYPES = {
    zmq.SocketType.SERVER,
    zmq.SocketType.CLIENT,
    zmq.SocketType.RADIO,
    zmq.SocketType.DISH,
    zmq.SocketType.GATHER,
    zmq.SocketType.SCATTER,
    zmq.SocketType.DGRAM,
    zmq.SocketType.PEER,
    zmq.SocketType.CHANNEL,
}


class SocketMode(IntEnum):
    BIND = 0
    CONNECT = 1


# Define a type variable for the Socket class
T_Socket = TypeVar("T_Socket", bound="Socket")


class Socket(entity.Entity, Generic[T_Socket]):
    """
    Simplified asynchronous ZeroMQ socket class with dynamic configuration,
    chainable methods, and support for proxying between sockets.
    """

    # Shared ZeroMQ context per process
    _context: ClassVar[zmq.asyncio.Context] = zmq.asyncio.Context.instance()

    type: zmq.SocketType = data.Field(default=zmq.SocketType.PAIR)
    mode: SocketMode = data.Field(default=SocketMode.CONNECT)
    endpoint: str = data.Field(default_factory=str)
    is_closed: bool = False
    _socket: zmq.asyncio.Socket | None = data.PrivateAttr(default=None)

    @data.field_validator("type")
    def check_positive(cls, socket_type):
        if socket_type in DRAFT_SOCKET_TYPES and not zmq.has("draft"):
            raise RuntimeError(f"DRAFT support is not enabled; cannot create socket of type {socket_type.name}")
        return socket_type

    @data.model_validator(mode="after")
    def instantiate_internal_socket(self) -> Socket:
        self._socket = self._context.socket(self.type.value)
        return self

    @property
    def socket(self) -> zmq.asyncio.Socket:
        if self._socket is None:
            raise RuntimeError("Cannot use socket: Socket is None")
        if self.is_closed:
            raise RuntimeError("Cannot send data: Socket is closed.")
        return self._socket

    async def __aenter__(self: T_Socket) -> T_Socket:
        if self.is_closed:
            logger.warning("Entering with closed socket")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()

    @tracer.Sync.decorator.call_raise
    def bind(self: T_Socket, endpoint: str) -> T_Socket:
        """
        Bind the socket to an endpoint.

        Args:
            endpoint (str): The endpoint to bind to (e.g., 'tcp://*:5555').

        Returns:
            T_Socket: The current instance for method chaining.
        """
        self.mode = SocketMode.BIND
        self.endpoint = endpoint
        self.socket.bind(endpoint)
        return self

    @tracer.Sync.decorator.call_raise
    def connect(self: T_Socket, endpoint: str) -> T_Socket:
        """
        Connect the socket to an endpoint.

        Args:
            endpoint (str): The endpoint to connect to (e.g., 'tcp://127.0.0.1:5555').

        Returns:
            T_Socket: The current instance for method chaining.
        """
        self.mode = SocketMode.CONNECT
        self.endpoint = endpoint
        self.socket.connect(endpoint)
        return self

    @tracer.Sync.decorator.call_raise
    def subscribe(self: T_Socket, topic: bytes = b"") -> T_Socket:
        """
        Subscribe to a topic (for SUB and DISH sockets).

        Args:
            topic: The topic to subscribe to. Defaults to b"" (all topics).

        Returns:
            T_Socket: The current instance for method chaining.

        Raises:
            ValueError: If the socket type does not support subscription.
        """
        if self.type not in (
            zmq.SocketType.SUB,
            zmq.SocketType.XSUB,
            zmq.SocketType.DISH,
        ):
            raise ValueError("subscribe() can only be used with SUB, XSUB, or DISH sockets.")
        self.socket.setsockopt(zmq.SUBSCRIBE, topic)
        return self

    @tracer.Async.decorator.call_raise
    async def close(self) -> None:
        """
        Close the ZeroMQ socket and clean up resources.
        """
        if self.is_closed:
            return
        await tracer.Async.call_raise(self.socket.close)
        self.is_closed = True

    @tracer.Async.decorator.call_raise
    async def send(self, data: bytes) -> None:
        """
        Send data through the ZeroMQ socket.

        Args:
            data (bytes): The data to send.

        Raises:
            RuntimeError: If the socket is closed.
        """
        await self.socket.send(data)

    @tracer.Async.decorator.call_raise
    async def recv(self) -> bytes:
        """
        Receive data from the ZeroMQ socket.

        Returns:
            bytes: The received data.

        Raises:
            RuntimeError: If the socket is closed.
        """
        return await self.socket.recv()

    @tracer.Async.decorator.call_raise
    async def send_multipart(self, data: list[bytes]) -> None:
        """
        Send a multipart message through the ZeroMQ socket.

        Args:
            data (List[bytes]): The list of message frames to send.

        Raises:
            RuntimeError: If the socket is closed.
        """
        if self.is_closed:
            raise RuntimeError("Cannot send data: Socket is closed.")

        await self.socket.send_multipart(data)

    @tracer.Async.decorator.call_raise
    async def recv_multipart(self) -> list[bytes]:
        """
        Receive a multipart message from the ZeroMQ socket.

        Returns:
            List[bytes]: The list of message frames received.

        Raises:
            RuntimeError: If the socket is closed.
        """
        if self.is_closed:
            raise RuntimeError("Cannot receive data: Socket is closed.")

        return await self.socket.recv_multipart()

    @staticmethod
    async def proxy(frontend: "Socket", backend: "Socket") -> None:
        """
        Asynchronous implementation of a ZeroMQ proxy.

        Args:
            frontend (Socket): The frontend socket.
            backend (Socket): The backend socket.

        Raises:
            ValueError: If either socket is closed.
        """
        if frontend.is_closed or backend.is_closed:
            raise ValueError("Both frontend and backend sockets must be open for proxying.")

        poller = zmq.asyncio.Poller()
        poller.register(frontend.socket, zmq.POLLIN)
        poller.register(backend.socket, zmq.POLLIN)

        try:
            while True:
                events = dict(await poller.poll())

                # Forward messages from frontend to backend
                if frontend.socket in events and events[frontend.socket] == zmq.POLLIN:
                    message = await frontend.socket.recv_multipart()
                    await backend.socket.send_multipart(message)

                # Forward messages from backend to frontend
                if backend.socket in events and events[backend.socket] == zmq.POLLIN:
                    message = await backend.socket.recv_multipart()
                    await frontend.socket.send_multipart(message)
        except asyncio.CancelledError:
            logger.debug("Proxy task was cancelled.")
            raise

    @classmethod
    @tracer.Sync.decorator.call_raise
    def pair(cls: Type[T_Socket]) -> T_Socket:
        """
        ZMQ PAIR

        This test module demonstrates the PAIR pattern in ZeroMQ, which is designed for
        simple, synchronous, bidirectional communication between exactly two peers. The
        PAIR pattern is suitable for connecting two sockets in a one-to-one fashion,
        such as in inter-thread or inter-process communication.

        Key Concepts:
        - **Socket A and Socket B**: Two sockets connected in a PAIR, allowing for
        bidirectional communication.
        - **Bidirectional Communication**: Both sockets can send and receive messages
        to and from each other.
        - **Exclusive Pairing**: PAIR sockets are intended for exclusive connections
        between two peers. Connecting more than two peers can result in unpredictable
        behavior.

        Diagram of the PAIR Pattern:

                +----------------+         +----------------+
                |                |         |                |
                |    Socket A    | <-----> |    Socket B    |
                |  (PAIR socket) |         |  (PAIR socket) |
                |                |         |                |
                +-------+--------+         +--------+-------+
                        |                           ^
                        |                           |
                        +---------------------------+
        """
        return cls(type=zmq.SocketType.PAIR)

    @classmethod
    def pub(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a PUB socket for publishing messages using ZeroMQ.

        The PUB socket type in ZeroMQ is designed for broadcasting messages to multiple
        subscribers. It is ideal for scenarios where a single publisher needs to disseminate
        information to many subscribers efficiently.

        **Key Features:**
        - **Broadcast Capability:** Send messages to all connected SUB sockets.
        - **Asynchronous Delivery:** Publishers do not wait for subscribers to receive messages.
        - **Topic Filtering:** Subscribers can filter messages based on topics.

        **Use Cases:**
        - Real-time data feeds (e.g., stock prices, news updates).
        - Event notification systems.
        - Logging services where multiple consumers need to receive log messages.

        **Diagram of the PUB/SUB Pattern:**

            +------------+                +------------+
            |            |                |            |
            | PUB Socket |  --------->    | SUB Socket |
            |            |                |            |
            +------------+                +------------+
                |                              ^
                |                              |
                +------------------------------+
        """
        return cls(type=zmq.SocketType.PUB)

    @classmethod
    def sub(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a SUB socket for subscribing to messages using ZeroMQ.

        The SUB (Subscriber) socket type in ZeroMQ is designed to receive messages from one or
        more PUB (Publisher) sockets. It is ideal for scenarios where a client needs to receive
        broadcasted information filtered by specific topics.

        **Key Features:**
        - **Subscription Filtering:** Receive only messages that match specified topics.
        - **Multiple Subscriptions:** A single SUB socket can subscribe to multiple topics.
        - **Asynchronous Reception:** Subscribers receive messages as they are published.

        **Use Cases:**
        - Real-time dashboards receiving live data feeds.
        - Notification systems where clients subscribe to certain event types.
        - Logging systems where different components subscribe to specific log levels or sources.

        **Diagram of the PUB/SUB Pattern:**

            +------------+                +------------+
            |            |                |            |
            | PUB Socket |  --------->    | SUB Socket |
            |            |                |            |
            +------------+                +------------+
                |                              ^
                |                              |
                +------------------------------+
        """
        return cls(type=zmq.SocketType.SUB)

    @classmethod
    def req(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a REQ socket for sending requests using ZeroMQ.

        The REQ (Request) socket type in ZeroMQ is used to send requests to and receive
        replies from REP (Reply) sockets. It enforces a strict send-receive pattern, making
        it suitable for synchronous client-server communication.

        **Key Features:**
        - **Synchronous Communication:** Each request must be followed by a reply.
        - **Load Balancing:** When connected to multiple REP sockets, requests are load-balanced.
        - **Simplified Protocol:** Ensures a clear request-response cycle.

        **Use Cases:**
        - RPC (Remote Procedure Call) systems.
        - Synchronous APIs where clients wait for server responses.
        - Task distribution systems requiring request-reply semantics.

        **Diagram of the REQ/REP Pattern:**

            +------------+                +------------+
            |            |                |            |
            | REQ Socket |  --------->    | REP Socket |
            |            |                |            |
            +------------+                +------------+
                |                              ^
                |                              |
                +------------------------------+
        """
        return cls(type=zmq.SocketType.REQ)

    @classmethod
    def rep(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a REP socket for replying to requests using ZeroMQ.

        The REP (Reply) socket type in ZeroMQ is designed to receive requests from REQ (Request)
        sockets and send back corresponding replies. It enforces a strict receive-send pattern,
        making it suitable for synchronous server-side communication.

        **Key Features:**
        - **Synchronous Communication:** Each received request must be followed by a reply.
        - **Load Balancing:** When connected to multiple REQ sockets, replies are load-balanced.
        - **Simplified Protocol:** Ensures a clear receive-reply cycle.

        **Use Cases:**
        - RPC (Remote Procedure Call) servers.
        - Synchronous APIs where servers respond to client requests.
        - Task processing systems requiring reply semantics.

        **Diagram of the REQ/REP Pattern:**

            +------------+                +------------+
            |            |                |            |
            | REQ Socket |  --------->    | REP Socket |
            |            |                |            |
            +------------+                +------------+
                |                              ^
                |                              |
                +------------------------------+
        """
        return cls(type=zmq.SocketType.REP)

    @classmethod
    def dealer(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a DEALER socket for asynchronous request routing using ZeroMQ.

        The DEALER socket type in ZeroMQ is an advanced socket type that extends the REQ socket.
        It allows for asynchronous request sending and receiving, enabling more flexible
        communication patterns without the strict send-receive cycle.

        **Key Features:**
        - **Asynchronous Communication:** Send multiple requests without waiting for replies.
        - **Load Balancing:** Efficiently distribute requests across multiple REP or ROUTER sockets.
        - **Advanced Routing:** Supports complex routing patterns when combined with ROUTER sockets.

        **Use Cases:**
        - Building scalable, asynchronous client-server architectures.
        - Implementing load-balanced task distribution systems.
        - Complex messaging patterns requiring non-blocking communication.

        **Diagram of the DEALER/ROUTER Pattern:**

            +---------------+                +---------------+
            |               |                |               |
            | DEALER Socket |  <-------->    | ROUTER Socket |
            |               |                |               |
            +---------------+                +---------------+
        """
        return cls(type=zmq.SocketType.DEALER)

    @classmethod
    def router(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a ROUTER socket for advanced routing using ZeroMQ.

        The ROUTER socket type in ZeroMQ is an advanced socket that complements the DEALER socket.
        It provides greater control over message routing by handling explicit addressing of peers,
        making it suitable for complex messaging architectures.

        **Key Features:**
        - **Explicit Addressing:** Directly address and communicate with specific DEALER or REQ sockets.
        - **Asynchronous Handling:** Manage multiple incoming and outgoing messages concurrently.
        - **Flexible Routing:** Implement custom routing logic based on message content or metadata.

        **Use Cases:**
        - Building centralized brokers or routers in messaging systems.
        - Implementing custom load-balancing and routing strategies.
        - Complex server architectures requiring precise control over client communication.

        **Diagram of the ROUTER/DEALER Pattern:**

            +---------------+                +--------------+
            |               |                |              |
            | ROUTER Socket |  <-------->    | DEALER Socket|
            |               |                |              |
            +---------------+                +--------------+
        """
        return cls(type=zmq.SocketType.ROUTER)

    @classmethod
    def pull(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a PULL socket for receiving messages using ZeroMQ.

        The PULL socket type in ZeroMQ is designed to receive messages in a pipeline pattern.
        It works in conjunction with PUSH sockets to distribute tasks among workers, enabling
        efficient and load-balanced message processing.

        **Key Features:**
        - **Pipeline Pattern:** Receive messages in a one-way flow from PUSH sockets.
        - **Load Balancing:** Distribute incoming messages evenly across multiple PULL sockets.
        - **Asynchronous Reception:** Continuously receive messages without blocking.

        **Use Cases:**
        - Task distribution systems where tasks are pushed to workers.
        - Parallel processing pipelines handling large volumes of data.
        - Event processing systems requiring efficient message ingestion.

        **Diagram of the PUSH/PULL Pattern:**

            +------------+                +------------+
            |            |                |            |
            | PUSH Socket|  --------->    | PULL Socket|
            |            |                |            |
            +------------+                +------------+
        """
        return cls(type=zmq.SocketType.PULL)

    @classmethod
    def push(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a PUSH socket for sending messages using ZeroMQ.

        The PUSH socket type in ZeroMQ is designed to send messages in a pipeline pattern.
        It works in conjunction with PULL sockets to distribute tasks among workers, enabling
        efficient and load-balanced message processing.

        **Key Features:**
        - **Pipeline Pattern:** Send messages in a one-way flow to PULL sockets.
        - **Load Balancing:** Distribute outgoing messages evenly across multiple PULL sockets.
        - **Asynchronous Sending:** Continuously send messages without waiting for acknowledgments.

        **Use Cases:**
        - Task distribution systems where tasks are pushed to workers.
        - Parallel processing pipelines handling large volumes of data.
        - Event generation systems requiring efficient message dissemination.

        **Diagram of the PUSH/PULL Pattern:**

            +------------+                +------------+
            |            |                |            |
            | PUSH Socket|  --------->    | PULL Socket|
            |            |                |            |
            +------------+                +------------+
        """
        return cls(type=zmq.SocketType.PUSH)

    @classmethod
    def xpub(cls: Type[T_Socket]) -> T_Socket:
        """
        Create an XPUB socket for extended publishing using ZeroMQ.

        The XPUB socket type in ZeroMQ extends the PUB socket by providing additional
        capabilities for managing subscriptions. It allows publishers to receive subscription
        messages from subscribers, enabling dynamic control over the publishing process.

        **Key Features:**
        - **Subscription Feedback:** Receive messages when subscribers subscribe or unsubscribe.
        - **Dynamic Subscription Management:** Adjust publishing behavior based on active subscriptions.
        - **Enhanced Control:** Implement custom logic based on subscriber activity.

        **Use Cases:**
        - Building responsive publishing systems that adapt to subscriber behavior.
        - Implementing access control based on subscriber subscriptions.
        - Monitoring subscriber activity for analytics or logging purposes.

        **Diagram of the XPUB/SUB Pattern:**

            +-------------+                +------------+
            |             |                |            |
            |  XPUB Socket|  <----->       | SUB Socket |
            |             |                |            |
            +-------------+                +------------+
        """
        return cls(type=zmq.SocketType.XPUB)

    @classmethod
    def xsub(cls: Type[T_Socket]) -> T_Socket:
        """
        Create an XSUB socket for extended subscribing using ZeroMQ.

        The XSUB socket type in ZeroMQ extends the SUB socket by providing additional
        capabilities for managing subscriptions. It allows subscribers to send subscription
        messages to publishers, enabling dynamic control over the subscription process.

        **Key Features:**
        - **Dynamic Subscriptions:** Send and manage subscription and unsubscription messages.
        - **Bidirectional Control:** Control subscription behavior based on application logic.
        - **Enhanced Flexibility:** Implement custom subscription management strategies.

        **Use Cases:**
        - Building responsive subscribing systems that can adjust subscriptions in real-time.
        - Implementing complex subscription management logic based on application needs.
        - Enhancing monitoring and analytics by tracking subscription changes.

        **Diagram of the XSUB/PUB Pattern:**

            +-------------+                +------------+
            |             |                |            |
            |  XSUB Socket|  <----->       | PUB Socket |
            |             |                |            |
            +-------------+                +------------+
        """
        return cls(type=zmq.SocketType.XSUB)

    @classmethod
    def stream(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a STREAM socket for handling raw TCP connections using ZeroMQ.

        The STREAM socket type in ZeroMQ is designed for handling raw TCP connections,
        providing low-level access to the underlying transport layer. It is suitable for
        scenarios requiring fine-grained control over network communication.

        **Key Features:**
        - **Raw TCP Access:** Handle individual TCP connections directly.
        - **Bidirectional Communication:** Send and receive data streams without message framing.
        - **Flexible Protocol Implementation:** Implement custom communication protocols on top of TCP.

        **Use Cases:**
        - Building custom network protocols requiring specific control over data transmission.
        - Implementing transparent proxies or gateways that need direct access to TCP streams.
        - Developing applications that require persistent, low-level TCP connections.

        **Diagram of the STREAM Pattern:**

            +--------------+                +--------------+
            |              |                |              |
            | STREAM Socket| <----------->  | STREAM Socket|
            |              |                |              |
            +--------------+                +--------------+
        """
        return cls(type=zmq.SocketType.STREAM)

    @classmethod
    def server(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a SERVER socket for handling server-side communication using ZeroMQ.

        The SERVER socket type in ZeroMQ is designed to manage server-side communication,
        handling incoming connections and facilitating message exchanges with CLIENT sockets.
        It provides mechanisms for scalable and efficient server implementations.

        **Key Features:**
        - **Connection Management:** Handle multiple incoming CLIENT connections.
        - **Scalable Communication:** Efficiently manage high volumes of client messages.
        - **Flexible Messaging Patterns:** Support various communication patterns such as request-reply or publish-subscribe.

        **Use Cases:**
        - Building scalable server applications that handle numerous client connections.
        - Implementing RPC servers with efficient client request handling.
        - Developing real-time data distribution systems with multiple subscribers.

        **Diagram of the SERVER/CLIENT Pattern:**

            +--------------+                +--------------+
            |              |                |              |
            | SERVER Socket| <--------->    | CLIENT Socket|
            |              |                |              |
            +--------------+                +--------------+
        """
        return cls(type=zmq.SocketType.SERVER)

    @classmethod
    def client(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a CLIENT socket for handling client-side communication using ZeroMQ.

        The CLIENT socket type in ZeroMQ is designed to manage client-side communication,
        initiating connections to SERVER sockets and facilitating message exchanges.
        It provides mechanisms for scalable and efficient client implementations.

        **Key Features:**
        - **Connection Initiation:** Establish connections to SERVER sockets.
        - **Asynchronous Communication:** Send and receive messages without blocking.
        - **Flexible Messaging Patterns:** Support various communication patterns such as request-reply or publish-subscribe.

        **Use Cases:**
        - Building scalable client applications that communicate with centralized servers.
        - Implementing RPC clients with efficient request handling.
        - Developing real-time data consumption systems with dynamic subscriptions.

        **Diagram of the SERVER/CLIENT Pattern:**

            +--------------+                +--------------+
            |              |                |              |
            | SERVER Socket| <--------->    | CLIENT Socket|
            |              |                |              |
            +--------------+                +--------------+
        """
        return cls(type=zmq.SocketType.CLIENT)

    @classmethod
    def radio(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a RADIO socket for radio communication using ZeroMQ.

        The RADIO socket type in ZeroMQ is designed for high-throughput, multicast-style
        communication, enabling one-to-many or many-to-many message distribution. It is
        suitable for scenarios requiring efficient dissemination of messages to multiple peers.

        **Key Features:**
        - **Multicast Communication:** Send messages to multiple RADIO sockets simultaneously.
        - **High Throughput:** Designed for efficient handling of large volumes of messages.
        - **Scalable Distribution:** Easily scale message distribution to numerous peers.

        **Use Cases:**
        - Live streaming applications broadcasting media to multiple clients.
        - Multiplayer gaming servers distributing game state updates to players.
        - Real-time data distribution systems requiring rapid dissemination of information.

        **Diagram of the RADIO Pattern:**

            +-------------+        +-------------+        +-------------+
            |             |        |             |        |             |
            | RADIO Socket| ---->  | RADIO Socket| ---->  | RADIO Socket|
            |             |        |             |        |             |
            +-------------+        +-------------+        +-------------+
        """
        return cls(type=zmq.SocketType.RADIO)

    @classmethod
    def dish(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a DISH socket for dish communication using ZeroMQ.

        The DISH socket type in ZeroMQ is designed for efficient group communication,
        enabling one-to-many or many-to-many message distribution with a focus on low latency
        and high scalability. It is suitable for scenarios requiring robust and efficient
        multicast messaging.

        **Key Features:**
        - **Group Communication:** Facilitate communication within a group of peers.
        - **Low Latency:** Optimize message delivery for minimal delay.
        - **High Scalability:** Efficiently manage communication with a large number of peers.

        **Use Cases:**
        - Distributed sensor networks requiring synchronized data collection.
        - Collaborative applications where multiple users need to receive the same updates.
        - Real-time monitoring systems broadcasting alerts to multiple clients.

        **Diagram of the DISH Pattern:**

            +-------------+        +-------------+        +-------------+
            |             |        |             |        |             |
            | DISH Socket | ---->  | DISH Socket | ---->  | DISH Socket |
            |             |        |             |        |             |
            +-------------+        +-------------+        +-------------+
        """
        return cls(type=zmq.SocketType.DISH)

    @classmethod
    def gather(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a GATHER socket for collecting messages using ZeroMQ.

        The GATHER socket type in ZeroMQ is designed to collect messages from multiple
        sources, aggregating them into a single stream. It is ideal for scenarios where
        a central aggregator needs to receive data from various producers.

        **Key Features:**
        - **Message Aggregation:** Collect messages from multiple GATHERER sockets.
        - **Centralized Collection:** Consolidate data from various sources into a single point.
        - **Scalable Reception:** Efficiently handle high volumes of incoming messages.

        **Use Cases:**
        - Data aggregation systems collecting logs or metrics from multiple services.
        - Centralized monitoring dashboards receiving data from various sensors.
        - Batch processing systems where data from multiple producers is consolidated for processing.

        **Diagram of the GATHERER/GATHER Pattern:**

            +-----------------+        +---------------+
            |                 |        |               |
            | GATHERER Socket |  --->  | GATHER Socket |
            |                 |        |               |
            +-----------------+        +---------------+
        """
        return cls(type=zmq.SocketType.GATHER)

    @classmethod
    def scatter(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a SCATTER socket for distributing messages using ZeroMQ.

        The SCATTER socket type in ZeroMQ is designed to distribute messages to multiple
        destinations, effectively scattering data to various consumers. It is suitable for
        scenarios where a central distributor needs to send data to multiple receivers.

        **Key Features:**
        - **Message Distribution:** Send messages to multiple SCATTER sockets efficiently.
        - **Centralized Distribution:** Distribute data from a single source to multiple destinations.
        - **Scalable Sending:** Handle high volumes of outgoing messages with ease.

        **Use Cases:**
        - Content distribution networks broadcasting data to multiple nodes.
        - Real-time notification systems sending alerts to various subscribers.
        - Distributed caching systems where updates need to be propagated to multiple caches.

        **Diagram of the SCATTER Pattern:**

            +-----------------+        +----------------+
            |                 |        |                |
            |  SCATTER Socket |  --->  | SCATTER Socket |
            |                 |        |                |
            +-----------------+        +----------------+
        """
        return cls(type=zmq.SocketType.SCATTER)

    @classmethod
    def dgram(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a DGRAM socket for datagram communication using ZeroMQ.

        The DGRAM socket type in ZeroMQ is designed for connectionless, message-oriented
        communication using datagrams. It is ideal for scenarios requiring lightweight,
        non-persistent message transmission.

        **Key Features:**
        - **Connectionless Communication:** Send and receive messages without establishing a persistent connection.
        - **Message-Oriented:** Handle discrete messages rather than continuous streams.
        - **Low Overhead:** Minimal resource usage suitable for high-frequency messaging.

        **Use Cases:**
        - Real-time gaming where quick, stateless message exchanges are required.
        - IoT devices transmitting sensor data intermittently.
        - Lightweight notification systems where persistence is not necessary.

        **Diagram of the DGRAM Pattern:**

            +--------------+                +-------------+
            |              |                |             |
            | DGRAM Socket |    <----->     | DGRAM Socket|
            |              |                |             |
            +--------------+                +-------------+
        """
        return cls(type=zmq.SocketType.DGRAM)

    @classmethod
    def peer(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a PEER socket for peer-to-peer communication using ZeroMQ.

        The PEER socket type in ZeroMQ is designed for direct peer-to-peer communication,
        enabling symmetric message exchanges between peers without a centralized broker.
        It is suitable for scenarios requiring decentralized and flexible communication.

        **Key Features:**
        - **Symmetric Communication:** Both peers can send and receive messages equally.
        - **Decentralized Architecture:** No need for a central server or broker.
        - **Flexible Topology:** Supports various communication topologies including mesh and star.

        **Use Cases:**
        - Decentralized chat applications enabling direct communication between users.
        - Distributed systems where nodes need to communicate without a central coordinator.
        - Collaborative tools allowing real-time interaction between multiple participants.

        **Diagram of the PEER Pattern:**

            +--------------+                +-------------+
            |              |                |             |
            |  PEER Socket | <---------->   | PEER Socket |
            |              |                |             |
            +--------------+                +-------------+
        """
        return cls(type=zmq.SocketType.PEER)

    @classmethod
    def channel(cls: Type[T_Socket]) -> T_Socket:
        """
        Create a CHANNEL socket for channel-based communication using ZeroMQ.

        The CHANNEL socket type in ZeroMQ is designed for establishing dedicated communication
        channels between peers. It provides a streamlined interface for managing bi-directional
        message flows within a specific communication channel.

        **Key Features:**
        - **Dedicated Channels:** Establish specific communication channels between peers.
        - **Bi-directional Messaging:** Facilitate two-way message exchanges within channels.
        - **Channel Management:** Easily manage multiple channels within the same application.

        **Use Cases:**
        - Private messaging systems where each conversation is a separate channel.
        - Modular applications requiring isolated communication channels between components.
        - Collaborative environments where distinct channels are needed for different topics or groups.

        **Diagram of the CHANNEL Pattern:**

            +----------------+                +---------------+
            |                |                |               |
            | CHANNEL Socket |  <---------->  | CHANNEL Socket|
            |                |                |               |
            +----------------+                +---------------+
        """
        return cls(type=zmq.SocketType.CHANNEL)
