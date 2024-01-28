import os
import openai
from typing import Any, Dict, List, Optional

from bundle import Task
from dotenv import load_dotenv
from openai.types.beta.thread import Thread
from openai.types.beta.assistant import Assistant
from openai.types.beta.threads.thread_message import ThreadMessage
from openai.types.beta.threads.run import Run

from . import LOGGER


def load_key():
    load_dotenv()
    return os.getenv("OPENAI_KEY")


@Task.dataclass
class GPTClient(Task.Async):
    """
    A client class for interacting with OpenAI's Assistants API.

    Attributes:
        api_key (str): The API key for authenticating with OpenAI.
    """

    api_key: str = Task.field(default_factory=load_key)

    def __post_init__(self):
        super().__post_init__()
        openai.api_key = self.api_key

    async def create_assistant(self, name: str, instructions: str, model: str, tools: List[Dict[str, Any]]) -> Assistant:
        """
        Creates an assistant in the OpenAI API.

        Args:
            name (str): The name of the assistant.
            instructions (str): Instructions for the assistant.
            model (str): The model to be used by the assistant.
            tools (List[Dict[str, Any]]): A list of tools to enable for the assistant.

        Returns:
            str: The ID of the created assistant.
        """
        assistant = openai.beta.assistants.create(name=name, instructions=instructions, model=model, tools=tools)
        LOGGER.debug(f"assistant created: {type(assistant)}\n{assistant}")
        return assistant

    async def create_thread(self) -> Thread:
        """
        Creates a conversation thread.

        Returns:
            str: The ID of the created thread.
        """
        thread = openai.beta.threads.create()
        LOGGER.debug(f"thread created: {type(thread)=}\n{thread}")
        return thread

    async def add_message_to_thread(self, thread_id: str, role: str, content: str) -> ThreadMessage:
        """
        Adds a message to a specific thread.

        Args:
            thread_id (str): The ID of the thread.
            role (str): The role of the message sender (e.g., 'user', 'assistant').
            content (str): The content of the message.

        Returns:
            str: The ID of the created message.
        """
        message = openai.beta.threads.messages.create(thread_id=thread_id, role=role, content=content)
        LOGGER.debug(f"message created: {type(message)=}\n{message}")
        return message

    async def run_assistant(self, thread_id: str, assistant_id: str, instructions: Optional[str] = None) -> Run:
        """
        Runs the assistant on a given thread.

        Args:
            thread_id (str): The ID of the thread.
            assistant_id (str): The ID of the assistant.
            instructions (Optional[str]): Additional instructions for the assistant.

        Returns:
            str: The ID of the run.
        """
        run = openai.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id, instructions=instructions)
        LOGGER.debug(f"{run.id=}, {run.assistant_id=}")
        return run

    async def get_run_status(self, thread_id: str, run_id: str) -> Run:
        """
        Retrieves the status of a run.

        Args:
            thread_id (str): The ID of the thread.
            run_id (str): The ID of the run.

        Returns:
            str: The status of the run.
        """
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        LOGGER.debug(f"{run.id=}, {run.assistant_id=}")
        return run

    async def get_thread_messages(self, thread_id: str) -> List[ThreadMessage]:
        """
        Retrieves messages from a thread.

        Args:
            thread_id (str): The ID of the thread.

        Returns:
            List[Dict[str, Any]]: A list of messages from the thread.
        """
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        LOGGER.debug(f"get messages: {type(messages)=}\n{messages}")
        return messages
