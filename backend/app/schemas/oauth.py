"""Safe non-secret OAuth API schemas."""

from pydantic import BaseModel


class OAuthConnectionStatusResponse(BaseModel):
    connector_enabled: bool
    configuration_present: bool
    connected: bool
    status: str
    scope: str
    owner_timezone: str
