"""Safe non-secret OAuth API schemas."""

from pydantic import BaseModel


class OAuthConnectionStatusResponse(BaseModel):
    connected: bool
    status: str
    scope: str
