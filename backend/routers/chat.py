from fastapi import APIRouter, Request
from backend.schemas import ChatRequest, ChatResponse
from backend.services.ai_agent import ai_agent

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await ai_agent.process_query(request.query)
    return ChatResponse(**result)
