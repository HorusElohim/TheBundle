# legalai/model/base_model.py

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseLanguageModel(ABC):
    """
    Abstract interface for a single model that can both encode embeddings
    and generate text. Useful for unifying embeddings + conversation
    without double-loading weights.
    """

    @abstractmethod
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        Convert each text into a vector embedding.
        Returns a [len(texts), hidden_dim] numpy array.
        """
        pass

    @abstractmethod
    def generate_text(self, prompt: str, max_new_tokens: int = 100) -> str:
        """
        Generate text from a given prompt using the model's causal LM head.
        """
        pass
