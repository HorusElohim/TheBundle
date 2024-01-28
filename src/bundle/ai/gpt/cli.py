import asyncio
from . import LOGGER, DATA_PATH, AgentOrchestrator, agents
from .agent import Agent


async def test_simple_agent():
    # Initialize the Agent
    agent = Agent()

    # Create an assistant using the Agent
    await agent.create_assistant(
        name="SimpleAgent",
        instructions="Respond to user queries.",
        model="gpt-3.5-turbo-1106",
        tools=[Agent.Tools.code],
    )

    # Create Thread
    thread = agent.gpt_client.create_thread()

    # Initiate a conversation with the assistant
    await agent.initiate_thread(thread=thread)

    # Send a message to the agent
    message_content = """
Write a simple joke about software engineer.
    """
    await agent.send_message(message_content)

    # Start the run and wait for it to finish
    await agent.start_run()
    await agent.wait_finished()

    # Retrieve and display the messages from the thread
    message = await agent.get_latest_agent_message()

    LOGGER.info(f"Agent response: {message}")  # Assuming messages have a content attribute
    agent.dump_json(DATA_PATH / f"{agent.class_name}.{agent.name}.{agent.assistant.id}json")


async def test_orchestrator_agents():
    # Initialize specialized agents
    agents_dict = {
        "Marco": agents.MarcoAgent(),
        "Jason": agents.JasonAgent(),
        "Alice": agents.AliceAgent(),
    }

    # Define a common goal for the orchestrator
    goal = "Design and develop a flutter application in Dart of SmartShare app, an application made to share data using the Torrent Protocol"

    # Initialize the AgentOrchestrator with the specialized agents
    orchestrator = AgentOrchestrator(agents_dict, goal)

    # Run the orchestrator to conduct the meeting
    await orchestrator.conduct_meeting()

    await asyncio.sleep(0.5)
    messages = await orchestrator.gpt_client.get_thread_messages(orchestrator.thread.id)
    print(messages)
    for msg in messages:
        print(messages["content"]["value"])


def main():
    # asyncio.run(test_simple_agent())
    asyncio.run(test_orchestrator_agents())


if __name__ == "__main__":
    main()
