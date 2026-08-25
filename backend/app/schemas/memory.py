from pydantic import BaseModel


class MemoryReference(BaseModel):
    """Memory information shared across the intelligence pipeline."""

    memory_id: str
    version: int
    key: str