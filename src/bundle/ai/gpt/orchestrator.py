import asyncio
from typing import Dict, Any
from .agents import BaseAgent
from .agent import Agent, GPTClient, Thread, AgentStateMachine
from . import LOGGER


class AgentOrchestrator:
    def __init__(self, agents: Dict[str, BaseAgent], goal: str):
        self.agents = agents
        self.goal = goal
        self.gpt_client = GPTClient()
        self.thread = None  # Shared thread for all agents
        LOGGER.info(f"AgentOrchestrator created with goal: {self.goal}")
        LOGGER.info(f"{self.agents}")

    async def setup_thread(self):
        # Initialize a shared thread for all agents
        if not self.thread:
            self.thread = await self.gpt_client.create_thread()
            LOGGER.info(f"Shared thread created with ID: {self.thread.id}")

    async def create_agents(self):
        await self.setup_thread()
        LOGGER.info(f"Creating Agents: {len(self.agents)}\n")
        for name, agent in self.agents.items():
            LOGGER.info(f"creating agent: {name}")
            await agent.create()

    async def conduct_meeting(self):
        await self.setup_thread()
        await self.create_agents()
        LOGGER.info(f"Starting project: {self.goal}\n")
        idx = 0
        for name, agent in self.agents.items():
            # Ensure each agent is using the shared thread
            agent.thread = self.thread
            question = self.formulate_question(name) if idx == 0 else self.formulate_continuos(name)
            await agent.initiate_thread(self.thread)
            LOGGER.info(f"{name}: agent.initiate_thread(self.thread)")
            await agent.send_message(question)
            LOGGER.info(f"{name}: agent.send_message(question)")
            await agent.start_run()
            LOGGER.info(f"{name}: agent.start_run()")
            await asyncio.sleep(1)
            LOGGER.info(f"{name}: await asyncio.sleep(1)")
            await agent.wait_finished()
            LOGGER.info(f"{name}: await agent.wait_finished()")
            # await self.share_knowledge(name)
            idx += 1

    def formulate_question(self, agent_name: str) -> str:
        # Formulate a question based on the agent's role and expertise
        return f"{self.goal} - {agent_name}, based on your expertise, what would be your approach?"

    def formulate_continuos(self, agent_name: str) -> str:
        # Formulate a question based on the agent's role and expertise
        return f"{self.goal} - {agent_name}, based on your expertise and the previous prompt what would be your approach?"

    async def share_knowledge(self, current_agent: str):
        LOGGER.info(f"{current_agent} is sharing insights with the team.\n")
        for name, agent in self.agents.items():
            if name != current_agent:
                # Share the current agent's response with the others
                shared_knowledge = await self.agents[current_agent].get_latest_agent_message()
                await agent.send_message(shared_knowledge.content)  # This sends the knowledge as a message in the thread
                await agent.wait_finished()  # Wait for the message to be processed
