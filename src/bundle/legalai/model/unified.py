import math
import torch
import numpy as np
from typing import List, Optional
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

from .base import BaseLanguageModel
from ..config import get_config
from bundle.core import logger

log = logger.get_logger(__name__)


class UnifiedLanguageModel(BaseLanguageModel):
    """
    A single model that provides both:
      - Embedding extraction (via last hidden state)
      - Text generation (via causal LM)
    Therefore, we do not load weights twice.
    """

    def __init__(self) -> None:
        """
        Initialize the UnifiedLanguageModel:
          1) Load config and decide device automatically (CPU, GPU, MPS).
          2) Set dtype to FP16 when GPU/MPS is available, else FP32.
          3) Load AutoTokenizer and AutoModelForCausalLM once.
        """
        config = get_config()  # Typed config object
        self.model_name: str = config.model_name
        self.batch_size: int = config.batch_size
        self.max_new_tokens: int = config.max_new_tokens

        # Decide device automatically (CPU, GPU, MPS, etc.)
        if torch.cuda.is_available():
            self.device: str = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        # FP16 vs. FP32: If GPU or MPS is used, we can do half precision
        self.dtype = torch.float16 if (self.device != "cpu") else torch.float32

        log.debug(f"Loading {self.model_name} on {self.device} with dtype={self.dtype}")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        # Ensure that pad_token_id is set
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # Model (AutoModelForCausalLM) - Single load
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, torch_dtype=self.dtype).to(self.device)
        self.model.eval()

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of texts into embeddings using the last hidden state of the causal model.

        Steps:
          1) Tokenize in batches
          2) Forward pass with output_hidden_states=True
          3) Mean-pool the last hidden states for each sequence
          4) Return an N x D NumPy array (N=number of texts, D=hidden dim)
        """
        log.debug("encode_texts input: %s", str(texts))

        embeddings_list = []
        total_batches = math.ceil(len(texts) / self.batch_size)

        # Use tqdm to show progress over the batches
        for batch_idx in tqdm(range(total_batches), desc="Encoding texts"):
            start = batch_idx * self.batch_size
            end = start + self.batch_size
            batch_texts = texts[start:end]

            inputs = self.tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=512).to(
                self.device
            )

            with torch.no_grad():
                outputs = self.model(
                    input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], output_hidden_states=True
                )
                # Final layer hidden states -> shape [B, seq_len, hidden_dim]
                last_hidden = outputs.hidden_states[-1]
                # Mean-pool across seq_len -> shape [B, hidden_dim]
                batch_emb = last_hidden.mean(dim=1)

            embeddings_list.append(batch_emb.cpu().numpy())

        return np.concatenate(embeddings_list, axis=0)

    def generate_text(self, prompt: str, max_new_tokens: Optional[int] = None) -> str:
        """
        Basic text generation method using model.generate().

        :param prompt: The text prompt to feed into the model.
        :param max_new_tokens: The maximum number of tokens to generate (overrides config if provided).
        :return: The generated text as a string.
        """
        max_new = max_new_tokens if max_new_tokens is not None else self.max_new_tokens
        log.debug("prompt: %s", prompt)

        # Pass padding and truncation to create attention_mask automatically
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True).to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_new,
                do_sample=False,
                # temperature=0.7,  # set to 0.7 or 1.0 if you want sampling
                pad_token_id=self.tokenizer.pad_token_id,  # Avoids HF warning about no pad_token_id
            )

        return self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
