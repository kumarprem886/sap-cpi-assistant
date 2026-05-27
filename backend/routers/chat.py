from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.claude_service import stream_generate, generate

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class QuickAskRequest(BaseModel):
    question: str
    context: str = ""


@router.post("/ask")
def quick_ask(req: QuickAskRequest):
    prompt = req.question
    if req.context:
        prompt = f"Context:\n{req.context}\n\nQuestion: {req.question}"
    result = generate("", prompt)
    return {"result": result, "type": "markdown"}


@router.post("/stream")
def stream_chat(req: ChatRequest):
    def event_stream():
        for chunk in stream_generate("", req.message):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class CodeReviewRequest(BaseModel):
    code: str
    code_type: str = "groovy"
    context: str = ""


@router.post("/review")
def review_code(req: CodeReviewRequest):
    prompt = f"""Review this SAP CPI {req.code_type.upper()} code for quality, correctness, and best practices:

```{req.code_type}
{req.code}
```

Context: {req.context or "General SAP CPI usage"}

Provide:
1. Overall quality score (1-10)
2. Issues found (critical / warning / suggestion)
3. Best practice violations
4. Improved version of the code
5. Security considerations
"""
    result = generate("", prompt)
    return {"result": result, "type": "markdown"}
