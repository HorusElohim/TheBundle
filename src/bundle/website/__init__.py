"""Public website package entrypoint."""

from fastapi import FastAPI

from .core import create_app


def get_app() -> FastAPI:
    """Create the default Bundle website FastAPI application."""
    return create_app()


__all__ = ["get_app"]
