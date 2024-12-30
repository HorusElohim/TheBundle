from typing import List, Dict
from rouge_score import rouge_scorer

from bundle.core import logger

log = logger.get_logger(__name__)


def compute_rouge(preds: List[str], refs: List[str]) -> Dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge1, rouge2, rougeL = 0.0, 0.0, 0.0
    for p, r in zip(preds, refs):
        scores = scorer.score(r, p)
        rouge1 += scores["rouge1"].fmeasure
        rouge2 += scores["rouge2"].fmeasure
        rougeL += scores["rougeL"].fmeasure
    N = len(preds)

    results = {
        "rouge1": rouge1 / N,
        "rouge2": rouge2 / N,
        "rougeL": rougeL / N,
    }
    log.debug("%s", str(results))

    return results
