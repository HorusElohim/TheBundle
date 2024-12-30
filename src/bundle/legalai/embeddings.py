import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from .config import LegalAIConfig


class LlamaEmbeddingWrapper:
    def __init__(self, model_name: str = LegalAIConfig.EMBEDDING_MODEL_NAME):
        print(f"[Embeddings] Loading embedding model: {model_name}")
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device != "cpu" else torch.float32,
            device_map="auto" if device != "cpu" else None,
        ).to(self.device)
        self.model.eval()

    def encode_texts(self, texts: list[str], batch_size: int = LegalAIConfig.BATCH_SIZE) -> np.ndarray:
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                last_hidden_state = outputs.last_hidden_state
                emb = last_hidden_state.mean(dim=1).cpu().numpy()  # Mean pooling
            all_embeddings.append(emb)
        return np.concatenate(all_embeddings, axis=0)
