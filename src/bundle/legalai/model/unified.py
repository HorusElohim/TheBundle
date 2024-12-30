# legalai/model/unified_model.py

import torch
import numpy as np
from typing import List
from transformers import AutoTokenizer, AutoModelForCausalLM

from .base import BaseLanguageModel
from ..config import get_config


class UnifiedLanguageModel(BaseLanguageModel):
    """
    A single model that provides both:
      - Embedding extraction (via last hidden state)
      - Text generation (via causal LM)
    Therefore, we do not load weights twice.
    """

    def __init__(self):
        config = get_config()  # Get our typed config object
        self.model_name = config.model_name
        self.batch_size = config.batch_size
        self.max_new_tokens = config.max_new_tokens

        # Decide device automatically (CPU, GPU, MPS, etc.)
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        # FP16 vs. FP32: If GPU or MPS is used, we can do half precision
        self.dtype = torch.float16 if (self.device != "cpu") else torch.float32

        print(f"[UnifiedLanguageModel] Loading {self.model_name} on {self.device} with dtype={self.dtype}")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # Model (AutoModelForCausalLM) - Single load
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype=self.dtype, device_map="auto" if self.device != "cpu" else None
        ).to(self.device)

        self.model.eval()

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        1) Tokenize in batches
        2) Forward pass with output_hidden_states=True
        3) Mean-pool last hidden states
        """
        embeddings_list = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            inputs = self.tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs, output_hidden_states=True)
                # final layer hidden states
                last_hidden = outputs.hidden_states[-1]  # shape [B, seq_len, hidden_dim]
                # mean pool across seq_len
                batch_emb = last_hidden.mean(dim=1)  # shape [B, hidden_dim]
            embeddings_list.append(batch_emb.cpu().numpy())

        return np.concatenate(embeddings_list, axis=0)

    def generate_text(self, prompt: str, max_new_tokens: int | None = None) -> str:
        """
        Basic text generation method using model.generate().
        """
        max_new_tokens = max_new_tokens if max_new_tokens is not None else self.max_new_tokens
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                inputs["input_ids"],
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=0.0,  # set to 0.7 or 1.0 if you want sampling
            )

        return self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
