from pydantic import BaseModel, Field

from .conversation import ConversationContext
from .intelligence import IntelligenceContext
from .knowledge import KnowledgeContext
from .request import RequestContext
from .response import ResponseContext
from .runtime import RuntimeContext


class ExecutionContext(BaseModel):
    """Shared execution context for a single intelligence pipeline."""

    request: RequestContext
    conversation: ConversationContext
    knowledge: KnowledgeContext
    intelligence: IntelligenceContext
    response: ResponseContext
    runtime: RuntimeContext = Field(
        default_factory=RuntimeContext,
    )