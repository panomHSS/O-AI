"""Concrete implementations of versioned internal adapter contracts."""

from app.adapters.chatgpt import ChatGPTAdapter
from app.adapters.local_ai import LocalAIAdapter

__all__ = ["ChatGPTAdapter", "LocalAIAdapter"]
