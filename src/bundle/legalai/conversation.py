# legalai/conversation.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class ConversationTurn:
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ConversationMemory:
    turns: List[ConversationTurn] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(ConversationTurn(role=role, content=content))

    def to_prompt(self) -> str:
        result = ""
        for turn in self.turns:
            result += f"{turn.role.capitalize()}: {turn.content}\n"
        return result
