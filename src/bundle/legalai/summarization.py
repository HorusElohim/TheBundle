# legalai/summarisation.py

from typing import List
from .config import get_config
from .model import UnifiedLanguageModel


class Summarizer:
    """
    A Summarizer that uses the UnifiedLanguageModel for text generation,
    avoiding a second load of the same weights.
    """

    def __init__(self, model: UnifiedLanguageModel):
        # Instead of loading a separate model, we instantiate one UnifiedLanguageModel
        print(f"[Summarizer] Using UnifiedLanguageModel for generation: {get_config().model_name}")
        self.model = model

    def summarize_context(self, context_texts: List[str], user_query: str, max_new_tokens: int | None = None) -> str:
        """
        Builds a system prompt referencing the provided context texts,
        then calls the UnifiedLanguageModel's generation to produce a summary.
        """
        max_new_tokens = max_new_tokens or get_config().max_new_tokens
        joined_context = "\n".join([f"- {ctx}" for ctx in context_texts if ctx])
        prompt = (
            f"System: You are a legal AI. Use the provided context to answer succinctly.\n"
            f"Context:\n{joined_context}\n\n"
            f"User: {user_query}\nAssistant:"
        )

        # Now we simply call the generate_text method on our unified model.
        summary = self.model.generate_text(prompt, max_new_tokens=max_new_tokens)
        return summary
