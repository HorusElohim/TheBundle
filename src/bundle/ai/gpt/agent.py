from enum import Enum, auto
from typing import List, Dict, Any
import asyncio
import bundle
from colorama import Fore, Back, Style

from . import LOGGER
from .client import GPTClient, Assistant, Thread, ThreadMessage, Run


def colored_agent(msg: str) -> str:
    return f"{Fore.BLACK}{Back.MAGENTA}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


class AgentState(Enum):
    IDLE = auto()
    AWAITING_USER_MESSAGE = auto()
    AWAITING_RUN_CREATION = auto()
    RUN_IN_PROGRESS = auto()
    ERROR = auto()


class AgentTools:
    code = {"type": "code_interpreter"}


class AgentModels(Enum):
    gpt3_turbo = "gpt-3.5-turbo-1106"


class AgentStateMachine:
    """
    Manages the state transitions for an Agent interacting with OpenAI's API.

    Attributes:
        state (AgentState): The current state of the Agent.
    """

    def __init__(self) -> None:
        """
        Initializes the AgentStateMachine with an idle state.
        """
        self.state: AgentState = AgentState.IDLE

    def transition_to_awaiting_user_message(self) -> None:
        """
        Transitions the state to AWAITING_USER_MESSAGE.
        """
        if self.state not in [AgentState.IDLE, AgentState.RUN_IN_PROGRESS]:
            raise Exception("Invalid state transition.")
        self.state = AgentState.AWAITING_USER_MESSAGE

    def transition_to_awaiting_run_creation(self) -> None:
        """
        Transitions the state to AWAITING_RUN_CREATION.
        """
        if self.state != AgentState.AWAITING_USER_MESSAGE:
            raise Exception("Invalid state transition.")
        self.state = AgentState.AWAITING_RUN_CREATION

    def transition_to_run_in_progress(self) -> None:
        """
        Transitions the state to RUN_IN_PROGRESS.
        """
        if self.state != AgentState.AWAITING_RUN_CREATION:
            raise Exception("Invalid state transition.")
        self.state = AgentState.RUN_IN_PROGRESS

    def transition_to_error(self) -> None:
        """
        Transitions the state to ERROR.
        """
        self.state = AgentState.ERROR


@bundle.dataclass
class Agent(bundle.Task.Async):
    """
    An agent capable of managing conversations with OpenAI's GPT models, using a state machine for state management.

    Attributes:
        thread_id (str | None): The ID of the current conversation thread.
    """

    gpt_client: GPTClient = bundle.Data.field(default_factory=GPTClient)
    state_machine: AgentStateMachine = bundle.Data.field(default_factory=AgentStateMachine)
    assistant: Assistant | None = None
    thread: Thread | None = None
    current_run: Run | None = None
    State = AgentState
    Tools = AgentTools
    Models = AgentModels

    def __post_init__(self) -> None:
        """
        Post Initializes the Agent with a GPTClient and an optional thread for attaching to an existing conversation.
        """
        super().__post_init__()
        if self.thread:
            self.state_machine.transition_to_awaiting_user_message()

    @property
    def agent_log(self):
        return colored_agent(f"{self.class_name}.{self.name}({self.assistant.id})")

    async def create_assistant(self, name: str, instructions: str, model: str, tools: List[AgentTools]) -> Assistant:
        """
        Creates an assistant with the specified parameters.

        Args:
            name (str): The name of the assistant.
            instructions (str): Instructions for the assistant.
            model (str): The model to be used by the assistant.
            tools (List[Dict[str, Any]]): A list of tools to enable for the assistant.

        Returns:
            Assistant: The created Assistant object.
        """
        self.name = name
        self.assistant = await self.gpt_client.create_assistant(name, instructions, model, tools)
        LOGGER.info(f"{self.agent_log} Assistant '{name}' with model '{model}' created")
        return self.assistant

    async def initiate_thread(self, thread: Thread | None) -> None:
        """
        Initiates a new conversation or attaches to an existing one based on the provided assistant ID.

        Args:
            assistant_id (str): The ID of the assistant to use in the conversation.
        """
        LOGGER.info(f"Initiating conversation with assistant ID: {self.assistant.id}")
        if self.thread is None:
            if thread is None:
                raise RuntimeError("Thread is required, cannot be None")
            else:
                self.thread = await self.gpt_client.create_thread()
                LOGGER.info(f"{self.agent_log} New thread created with ID: {self.thread.id}")
        self.state_machine.transition_to_awaiting_user_message()
        LOGGER.info(f"{self.agent_log} Agent is ready to receive user messages.")

    async def send_message(self, message: str) -> ThreadMessage:
        """
        Sends a message to the current conversation thread.

        Args:
            message (str): The message content to send.

        Returns:
            ThreadMessage: The created ThreadMessage object.
        """
        LOGGER.info(f"{self.agent_log} Sending message: {message}")
        if self.state_machine.state != AgentState.AWAITING_USER_MESSAGE:
            raise Exception("Agent is not ready to send a message.")
        if not self.thread.id:
            raise Exception("Thread ID is not set.")
        message_object = await self.gpt_client.add_message_to_thread(self.thread.id, "user", message)
        LOGGER.info(f"{self.agent_log} Message sent and awaiting run creation. Message ID: {message_object.id}")
        self.state_machine.transition_to_awaiting_run_creation()
        return message_object

    async def start_run(self, instructions: str | None = None) -> Run:
        """
        Starts a new run with the assistant in the current conversation thread.

        Args:
            instructions (str | None): Additional instructions for the assistant.

        Returns:
            Run: The created Run object.
        """
        LOGGER.info("Starting a new run with the assistant.")
        if self.state_machine.state != AgentState.AWAITING_RUN_CREATION:
            raise Exception("Agent is not ready to start a run.")
        if not self.thread.id or not self.assistant.id:
            raise Exception("Thread ID or Assistant ID is not set.")
        self.current_run = await self.gpt_client.run_assistant(self.thread.id, self.assistant.id, instructions)
        self.state_machine.transition_to_run_in_progress()
        LOGGER.info(f"{self.agent_log} Run started. Run ID: {self.current_run.id}")
        return self.current_run

    async def wait_finished(self) -> None:
        """
        Waits until the current run is finished before proceeding.
        """
        LOGGER.info(f"{self.agent_log} Waiting for the current run to finish.")
        while self.state_machine.state == AgentState.RUN_IN_PROGRESS:
            await self.poll_run_status()
            await asyncio.sleep(1.6)  # Sleep for a short period to avoid overwhelming the API with requests

    async def poll_run_status(self) -> None:
        """
        Polls the current run's status and updates the Agent's state accordingly.
        """
        if self.state_machine.state != AgentState.RUN_IN_PROGRESS:
            raise Exception("No run in progress to poll.")
        if not self.current_run:
            raise Exception("Current run is not set.")
        run_status = await self.gpt_client.get_run_status(self.thread.id, self.current_run.id)
        LOGGER.debug(f"{self.agent_log} Polling run status: {run_status.status}")
        if run_status.status == "completed":
            self.state_machine.transition_to_awaiting_user_message()
            LOGGER.info(f"{self.agent_log} Run completed successfully.")
        elif run_status.status in ["failed", "expired", "cancelled"]:
            self.state_machine.transition_to_error()
            LOGGER.error(f"{self.agent_log} Run encountered an error or was cancelled. Status: {run_status.status}")

    async def get_conversation_history(self) -> List[ThreadMessage]:
        """
        Retrieves the conversation history from the current thread.

        Returns:
            List[ThreadMessage]: A list of messages from the conversation thread.
        """
        if not self.thread.id:
            raise Exception("No thread initiated.")
        LOGGER.info(f"{self.agent_log} Retrieving conversation history.")
        messages = await self.gpt_client.get_thread_messages(self.thread.id)
        return messages

    async def get_latest_agent_message(self) -> ThreadMessage | None:
        """
        Retrieves the latest message sent by the agent in the current conversation thread.

        Returns:
            ThreadMessage | None: The latest message sent by the agent, or None if no agent message is found.
        """
        if not self.thread.id:
            LOGGER.error(f"{self.agent_log} No thread initiated, unable to retrieve latest agent message.")
            return None

        messages = await self.get_conversation_history()
        # Filter for messages where the role is 'assistant'
        agent_messages = [msg for msg in messages if msg.role == "assistant"]

        if agent_messages:
            latest_message = agent_messages[-1]
            LOGGER.info(f"{self.agent_log} Latest agent message retrieved: {latest_message.content}")
            return latest_message
        else:
            LOGGER.info(f"{self.agent_log} No agent messages found in the thread.")
            return None
