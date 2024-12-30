import torch
import wandb
from typing import List
from transformers import (
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
    PreTrainedTokenizerBase,
)
from .config import get_config
from .summarization import Summarizer


class LegalAIDataset(torch.utils.data.Dataset):
    """
    Minimal dataset for (document -> summary) pairs.
    """

    def __init__(self, documents: List[str], summaries: List[str], tokenizer: PreTrainedTokenizerBase, max_len=512):
        self.documents = documents
        self.summaries = summaries
        self.tokenizer = tokenizer
        self.max_len = max_len
        # Decide device automatically (CPU, GPU, MPS, etc.)
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

    def __len__(self):
        return len(self.documents)

    def __getitem__(self, idx):
        source = self.documents[idx]
        target = self.summaries[idx]
        inputs = self.tokenizer(source, max_length=self.max_len, truncation=True, padding="max_length").to(self.device)
        labels = self.tokenizer(target, max_length=self.max_len, truncation=True, padding="max_length").to(self.device)
        return {
            "input_ids": torch.tensor(inputs["input_ids"]),
            "attention_mask": torch.tensor(inputs["attention_mask"]),
            "labels": torch.tensor(labels["input_ids"]),
        }


def fine_tune_model(train_docs: List[str], train_summaries: List[str]):
    """
    Demonstrates fine-tuning of the Summarizer's model on a custom dataset.
    """
    wandb.init(
        project=get_config().wandb_project,
        name=get_config().wandb_run,
    )

    # Initialize the Summarizer and its components
    summarizer = Summarizer()
    model = summarizer.model
    tokenizer = summarizer.tokenizer

    # Prepare the dataset
    dataset = LegalAIDataset(train_docs, train_summaries, tokenizer)
    collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")

    # Configure training arguments
    training_args = TrainingArguments(
        output_dir="./checkpoints",
        num_train_epochs=3,  # Increase for better training
        per_device_train_batch_size=8,  # Adjust batch size based on memory
        save_steps=50,
        logging_steps=10,
        evaluation_strategy="no",  # Adjust if evaluation dataset is available
        report_to="wandb",
        learning_rate=5e-5,
        weight_decay=0.01,
        save_total_limit=2,  # Keep only the 2 latest checkpoints
        load_best_model_at_end=False,
    )

    # Initialize the Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator,
        processing_class=tokenizer,  # Replaces the deprecated `tokenizer`
    )

    # Fine-tune the model
    trainer.train()

    # Save the final model
    trainer.save_model("./checkpoints/final")
    wandb.finish()
