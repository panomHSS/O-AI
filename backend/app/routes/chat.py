from fastapi import APIRouter
from pydantic import BaseModel
router=APIRouter()
class ChatRequest(BaseModel): message:str
@router.post('/chat')
def c(r:ChatRequest): return {'reply':'Hello from Backend: '+r.message}
