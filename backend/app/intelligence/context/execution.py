from pydantic import BaseModel

from .conversation import ConversationContext
from .intelligence import IntelligenceContext
from .knowledge import KnowledgeContext
from .request import RequestContext
from .response import ResponseContext


class ExecutionContext(BaseModel):
    """Shared execution context for a single intelligence pipeline."""

    request: RequestContext
    conversation: ConversationContext
    knowledge: KnowledgeContext
    intelligence: IntelligenceContext
    response: ResponseContext