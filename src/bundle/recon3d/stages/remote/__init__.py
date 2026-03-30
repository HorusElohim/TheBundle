"""Remote execution stages for cloud GPU training."""

from .lambda_runner import LambdaConfig, LambdaRunner

__all__ = ["LambdaConfig", "LambdaRunner"]
