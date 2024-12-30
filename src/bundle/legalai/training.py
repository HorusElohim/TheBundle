# legalai/training.py
import torch
import wandb
from typing import List
from transformers import Trainer, TrainingArguments, DataCollatorWithPadding
from .config import LegalAIConfig
from .summarization import Summarizer


class LegalAIDataset(torch.utils.data.Dataset):
    """
    Minimal dataset for (document -> summary) pairs.
    """

    def __init__(self, documents: List[str], summaries: List[str], tokenizer, max_len=512):
        self.documents = documents
        self.summaries = summaries
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.documents)

    def __getitem__(self, idx):
        source = self.documents[idx]
        target = self.summaries[idx]
        inputs = self.tokenizer(source, max_length=self.max_len, truncation=True)
        labels = self.tokenizer(target, max_length=self.max_len, truncation=True)
        return {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "labels": labels["input_ids"],
        }


def fine_tune_model(train_docs: List[str], train_summaries: List[str]):
    """
    Sample method to demonstrate partial fine-tuning of the Summarizer's model.
    """
    wandb.init(
        project=LegalAIConfig.WAND_PROJECT,
        name=LegalAIConfig.WAND_RUNNAME,
    )
    summarizer = Summarizer()
    tokenizer = summarizer.tokenizer
    model = summarizer.model

    dataset = LegalAIDataset(train_docs, train_summaries, tokenizer)
    collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")

    training_args = TrainingArguments(
        output_dir="./checkpoints",
        num_train_epochs=1,  # For demonstration
        per_device_train_batch_size=1,
        save_steps=10,
        logging_steps=5,
        evaluation_strategy="no",
        report_to="wandb",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=collator,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model("./checkpoints/final")
    wandb.finish()
