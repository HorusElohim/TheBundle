# legalai/conversation.py
from dataclasses import dataclass, field
from typing import List
from bundle.core import logger

log = logger.get_logger(__name__)


@dataclass
class ConversationTurn:
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ConversationMemory:
    turns: List[ConversationTurn] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(ConversationTurn(role=role, content=content))
        log.debug("role:'%s' with content: '%s'", role, content)

    def to_prompt(self) -> str:
        result = ""
        for turn in self.turns:
            result += f"{turn.role.capitalize()}: {turn.content}\n"
        log.debug("result:'%s'", result)
        return result
