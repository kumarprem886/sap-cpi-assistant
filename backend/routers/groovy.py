from fastapi import APIRouter
from pydantic import BaseModel
from services.claude_service import generate

router = APIRouter(prefix="/api/groovy", tags=["groovy"])


class GroovyRequest(BaseModel):
    task: str
    context: str = ""
    script_type: str = "message_transform"


class GroovyExplainRequest(BaseModel):
    script: str


class GroovyDebugRequest(BaseModel):
    script: str
    error: str
    message_payload: str = ""


GROOVY_SYSTEM = """Generate production-ready Groovy scripts for SAP CPI.
Always include required imports:
- import com.sap.gateway.ip.core.customdev.util.Message
- import java.util.HashMap
- import groovy.xml.XmlSlurper / groovy.json.JsonSlurper as needed

Always follow the standard SAP CPI Groovy script pattern:
def Message processData(Message message) { ... return message }

Handle exceptions properly. Add concise inline comments only for non-obvious logic.
Output ONLY the Groovy code."""


@router.post("/generate")
def generate_groovy(req: GroovyRequest):
    type_desc = {
        "message_transform": "message transformation (read body, transform, set new body)",
        "header_property": "setting/reading message headers and exchange properties",
        "http_call": "making HTTP calls using SAP CPI HTTP client",
        "json_xml": "converting between JSON and XML payloads",
        "exception_handler": "custom exception handling and error message formatting",
        "splitter": "splitting a message into multiple messages",
        "aggregator": "aggregating multiple messages into one",
    }.get(req.script_type, req.script_type)

    prompt = f"""Generate a SAP CPI Groovy script for: {req.task}

Script Type: {type_desc}
Additional Context: {req.context or "None"}

Requirements:
- Follow SAP CPI Groovy script conventions
- Use proper imports
- Handle null/empty cases
- Return the modified message object
"""
    result = generate(GROOVY_SYSTEM, prompt)
    return {"result": result, "type": "groovy"}


@router.post("/explain")
def explain_groovy(req: GroovyExplainRequest):
    prompt = f"""Explain this SAP CPI Groovy script in detail:

```groovy
{req.script}
```

Provide:
1. What this script does (plain English summary)
2. Step-by-step breakdown
3. SAP CPI APIs/methods used and their purpose
4. Potential edge cases or issues
5. Suggested improvements
"""
    result = generate("", prompt)
    return {"result": result, "type": "markdown"}


@router.post("/debug")
def debug_groovy(req: GroovyDebugRequest):
    prompt = f"""Debug this SAP CPI Groovy script that is throwing an error.

Script:
```groovy
{req.script}
```

Error Message:
{req.error}

Message Payload (if available):
{req.message_payload or "Not provided"}

Provide:
1. Root cause of the error
2. Fixed script
3. Explanation of what was wrong
"""
    result = generate(GROOVY_SYSTEM, prompt)
    return {"result": result, "type": "debug"}
