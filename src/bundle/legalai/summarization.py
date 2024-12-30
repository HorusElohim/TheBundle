import torch
from typing import List
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from .config import LegalAIConfig


class Summarizer:
    def __init__(self):
        print(f"[Summarizer] Loading generation model: {LegalAIConfig.MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(LegalAIConfig.MODEL_NAME)
        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.model = AutoModelForCausalLM.from_pretrained(
            LegalAIConfig.MODEL_NAME,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        self.model.eval()

    def summarize_context(self, context_texts: List[str], user_query: str, max_new_tokens: int = None) -> str:
        max_new_tokens = max_new_tokens or LegalAIConfig.MAX_NEW_TOKENS
        joined_context = "\n".join([f"- {ctx}" for ctx in context_texts if ctx])
        prompt = (
            f"System: You are a legal AI. Use the provided context to answer succinctly.\n"
            f"Context:\n{joined_context}\n\n"
            f"User: {user_query}\nAssistant:"
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        gen_cfg = GenerationConfig(max_new_tokens=max_new_tokens, temperature=0.0, do_sample=False, top_k=1)
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, generation_config=gen_cfg)
        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
