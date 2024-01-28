from .. import Agent


@Agent.dataclass
class BaseAgent(Agent):
    name: str = Agent.field(default_factory=str)
    model: Agent.Models = Agent.Models.gpt3_turbo
    tools: list[Agent.Tools] = Agent.field(default_factory=list)
    instruction: str = Agent.field(default_factory=str)

    async def create(self):
        assert self.name
        assert self.model
        assert self.instruction
        await self.create_assistant(self.name, self.instruction, self.model.value, self.tools)
