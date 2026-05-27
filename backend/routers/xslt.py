from fastapi import APIRouter
from pydantic import BaseModel
from services.claude_service import generate

router = APIRouter(prefix="/api/xslt", tags=["xslt"])


class XSLTRequest(BaseModel):
    description: str
    source_xml: str = ""
    target_xml: str = ""
    rules: str = ""


class XSLTExplainRequest(BaseModel):
    xslt: str


XSLT_SYSTEM = """Generate valid XSLT 2.0 for SAP CPI transformations.
- Use xsl:stylesheet version="2.0" with proper namespace declarations
- Include xsl:output with appropriate method (xml/text/html)
- Handle namespaces correctly
- Use xsl:template match patterns properly
- For complex transformations, use named templates and xsl:call-template
Output ONLY the XSLT code — no markdown, no explanation outside of XML comments."""


@router.post("/generate")
def generate_xslt(req: XSLTRequest):
    prompt = f"""Generate XSLT 2.0 for SAP CPI with the following specification:

Description / Goal:
{req.description}

Source XML Sample:
{req.source_xml or "Not provided — infer from description"}

Target XML Sample:
{req.target_xml or "Not provided — infer from description"}

Special Rules / Business Logic:
{req.rules or "None"}

Generate complete, working XSLT 2.0 that can be deployed directly in SAP CPI.
"""
    result = generate(XSLT_SYSTEM, prompt)
    return {"result": result, "type": "xml"}


@router.post("/explain")
def explain_xslt(req: XSLTExplainRequest):
    prompt = f"""Analyze and explain this XSLT used in SAP CPI:

```xml
{req.xslt}
```

Provide:
1. What this XSLT transforms (source to target description)
2. Breakdown of each template/rule
3. XPath expressions used and their meaning
4. Namespaces and their purpose
5. Potential issues or optimizations
"""
    result = generate("", prompt)
    return {"result": result, "type": "markdown"}


class XSLTFromSamplesRequest(BaseModel):
    source_xml: str
    target_xml: str


@router.post("/from-samples")
def xslt_from_samples(req: XSLTFromSamplesRequest):
    prompt = f"""Generate XSLT 2.0 that transforms the source XML into the target XML.

Source XML:
```xml
{req.source_xml}
```

Target XML (desired output):
```xml
{req.target_xml}
```

Analyze the structural differences and generate the XSLT transformation.
Handle all elements, attributes, and namespaces present in the samples.
"""
    result = generate(XSLT_SYSTEM, prompt)
    return {"result": result, "type": "xml"}
