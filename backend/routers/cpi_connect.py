"""
CPI Connect router — proxy calls to a live SAP Integration Suite tenant.

Reads credentials from backend/.env:
  CPI_BASE_URL          e.g. https://<tenant>.it-cpi018-rt.cfapps.eu10.hana.ondemand.com
  CPI_API_BASE_URL      e.g. https://<tenant>.it-cpi018.cfapps.eu10.hana.ondemand.com/api/v1
  CPI_AUTH_TYPE         "basic" | "oauth"   (default: basic)
  CPI_USER / CPI_PASS   for basic auth
  CPI_CLIENT_ID / CPI_CLIENT_SECRET / CPI_TOKEN_URL  for OAuth2
"""

from __future__ import annotations

import os
import re
import time
import base64 as _b64
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
import io as _io_mod
from pydantic import BaseModel
from typing import Optional

try:
    from dotenv import set_key as _dotenv_set_key, find_dotenv as _dotenv_find
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

def _env_file_path() -> str:
    """Locate the .env file for the backend."""
    # Walk up from this file's directory to find .env
    candidate = os.path.join(os.path.dirname(__file__), '..', '.env')
    candidate = os.path.normpath(candidate)
    if os.path.exists(candidate):
        return candidate
    # Fallback: find_dotenv
    if _DOTENV_AVAILABLE:
        found = _dotenv_find(usecwd=False, raise_error_if_not_found=False)
        if found:
            return found
    return candidate  # Return the expected path even if not yet created

router = APIRouter(prefix="/api/cpi", tags=["cpi-connect"])

# ── Credentials (read from env) ───────────────────────────────────────────────

def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def _api_base() -> str:
    return _cfg("CPI_API_BASE_URL").rstrip("/")

def _auth_type() -> str:
    return _cfg("CPI_AUTH_TYPE", "basic").lower()


# ── Token cache for OAuth ─────────────────────────────────────────────────────

_token_cache: dict = {"token": "", "expires_at": 0}

def _get_oauth_token() -> str:
    if time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]
    resp = httpx.post(
        _cfg("CPI_TOKEN_URL"),
        data={"grant_type": "client_credentials"},
        auth=(_cfg("CPI_CLIENT_ID"), _cfg("CPI_CLIENT_SECRET")),
        timeout=15,
    )
    resp.raise_for_status()
    j = resp.json()
    _token_cache["token"] = j["access_token"]
    _token_cache["expires_at"] = time.time() + int(j.get("expires_in", 3600))
    return _token_cache["token"]


def _headers() -> dict:
    h = {"Accept": "application/json"}
    if _auth_type() == "oauth":
        h["Authorization"] = f"Bearer {_get_oauth_token()}"
    return h

def _auth() -> tuple | None:
    if _auth_type() == "basic":
        return (_cfg("CPI_USER"), _cfg("CPI_PASS"))
    return None

def _get(path: str, params: dict | None = None):
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not configured in backend/.env")
    url = f"{base}{path}"
    resp = httpx.get(url, headers=_headers(), auth=_auth(), params=params, timeout=20)
    if resp.status_code == 401:
        raise HTTPException(401, "CPI authentication failed — check credentials in backend/.env")
    resp.raise_for_status()
    return resp.json()


def _csrf_write_headers(base: str, fetch_path: str = "/IntegrationPackages?$top=1&$format=json") -> dict:
    """Fetch a CSRF token and return write-ready headers."""
    csrf_resp = httpx.get(
        f"{base}{fetch_path}",
        headers={**_headers(), "X-CSRF-Token": "Fetch"},
        auth=_auth(),
        timeout=15,
    )
    token = csrf_resp.headers.get("x-csrf-token", "")
    return {**_headers(), "Content-Type": "application/json", "X-CSRF-Token": token, "Accept": "application/json"}


# ── Connection test ───────────────────────────────────────────────────────────

@router.get("/ping")
def ping_cpi():
    """Test connectivity to the configured CPI tenant."""
    if not _api_base():
        return {"connected": False, "reason": "CPI_API_BASE_URL not set in backend/.env"}
    try:
        _get("/IntegrationPackages?$top=1&$format=json")
        return {"connected": True, "tenant": _api_base()}
    except HTTPException as e:
        return {"connected": False, "reason": str(e.detail)}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


# ── Connection Settings (read / update .env) ──────────────────────────────────

_MASKED = "••••••••"

@router.get("/settings")
def get_cpi_settings():
    """Return current CPI connection settings. Secrets are masked."""
    return {
        "authType":     _cfg("CPI_AUTH_TYPE", "oauth"),
        "apiBaseUrl":   _cfg("CPI_API_BASE_URL"),
        "baseUrl":      _cfg("CPI_BASE_URL"),
        # OAuth
        "clientId":     _cfg("CPI_CLIENT_ID"),
        "clientSecret": _MASKED if _cfg("CPI_CLIENT_SECRET") else "",
        "tokenUrl":     _cfg("CPI_TOKEN_URL"),
        # Basic
        "user":         _cfg("CPI_USER"),
        "password":     _MASKED if _cfg("CPI_PASS") else "",
    }


class CpiSettingsRequest(BaseModel):
    authType:     str  = "oauth"
    apiBaseUrl:   str  = ""
    baseUrl:      str  = ""
    # OAuth
    clientId:     str  = ""
    clientSecret: str  = ""   # send _MASKED to keep existing value
    tokenUrl:     str  = ""
    # Basic
    user:         str  = ""
    password:     str  = ""   # send _MASKED to keep existing value


@router.put("/settings")
def update_cpi_settings(req: CpiSettingsRequest):
    """
    Persist updated CPI connection settings to backend/.env and reload into
    os.environ immediately — no backend restart needed.
    Secrets left as '••••••••' are not overwritten.
    """
    env_path = _env_file_path()

    def _set(key: str, value: str):
        """Write key=value to .env and to os.environ."""
        os.environ[key] = value
        if _DOTENV_AVAILABLE:
            _dotenv_set_key(env_path, key, value, quote_mode="never")

    _set("CPI_AUTH_TYPE",    req.authType.strip() or "oauth")
    _set("CPI_API_BASE_URL", req.apiBaseUrl.strip().rstrip("/"))
    _set("CPI_BASE_URL",     req.baseUrl.strip().rstrip("/") or req.apiBaseUrl.strip().rstrip("/"))

    if req.authType == "oauth":
        _set("CPI_CLIENT_ID",  req.clientId.strip())
        _set("CPI_TOKEN_URL",  req.tokenUrl.strip())
        if req.clientSecret and req.clientSecret != _MASKED:
            _set("CPI_CLIENT_SECRET", req.clientSecret.strip())
    else:  # basic
        _set("CPI_USER", req.user.strip())
        if req.password and req.password != _MASKED:
            _set("CPI_PASS", req.password.strip())

    # Clear OAuth token cache so the next request fetches a fresh token
    global _token_cache
    _token_cache = {"token": "", "expires_at": 0}

    # Quick connectivity test with the new settings
    try:
        _get("/IntegrationPackages?$top=1&$format=json")
        return {"status": "saved", "connected": True, "tenant": _cfg("CPI_API_BASE_URL")}
    except Exception as e:
        return {"status": "saved", "connected": False, "reason": str(e)}


# ── Packages ──────────────────────────────────────────────────────────────────

@router.get("/packages")
def list_packages():
    """List all integration packages on the tenant."""
    data = _get("/IntegrationPackages?$format=json")
    results = data.get("d", {}).get("results", [])
    return [
        {
            "id":          p.get("Id"),
            "name":        p.get("Name"),
            "description": p.get("Description"),
            "version":     p.get("Version"),
            "modified":    p.get("ModifiedAt"),
        }
        for p in results
    ]


@router.get("/packages/{package_id}/iflows")
def list_iflows(package_id: str):
    """List all iFlows in a package."""
    data = _get(f"/IntegrationPackages('{package_id}')/IntegrationDesigntimeArtifacts?$format=json")
    results = data.get("d", {}).get("results", [])
    return [
        {
            "id":      a.get("Id"),
            "name":    a.get("Name"),
            "version": a.get("Version"),
            "type":    a.get("ArtifactType"),
        }
        for a in results
    ]


# ── Package management ────────────────────────────────────────────────────────

class CreatePackageRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/packages")
def create_package(req: CreatePackageRequest):
    """Create a new integration package."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")

    pkg_id = re.sub(r"[^A-Za-z0-9_]", "_", req.name.strip())
    pkg_id = re.sub(r"_+", "_", pkg_id).strip("_")
    if pkg_id and pkg_id[0].isdigit():
        pkg_id = "_" + pkg_id
    pkg_id = pkg_id or "Package1"

    body = {
        "Id":                  pkg_id,
        "Name":                req.name,
        "Description":         req.description,
        "ShortText":           req.description,
        "Version":             "1.0.0",
        "SupportedPlatform":   "SAP Cloud Integration",
        "Products":            "",
        "Keywords":            "",
        "Countries":           "",
        "Industries":          "",
        "LineOfBusiness":      "",
    }
    headers = _csrf_write_headers(base)
    resp = httpx.post(f"{base}/IntegrationPackages", headers=headers, auth=_auth(), json=body, timeout=30)
    if resp.status_code in (200, 201):
        return {"status": "created", "id": pkg_id, "name": req.name}
    raise HTTPException(resp.status_code, f"Create package failed: {resp.text[:500]}")


@router.delete("/packages/{package_id}")
def delete_package(package_id: str):
    """Delete an integration package (must be empty)."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")
    headers = _csrf_write_headers(base)
    resp = httpx.delete(f"{base}/IntegrationPackages('{package_id}')", headers=headers, auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204):
        return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete package failed: {resp.text[:300]}")


# ── iFlow export ──────────────────────────────────────────────────────────────

@router.get("/packages/{package_id}/iflows/{iflow_id}/export")
def export_iflow(package_id: str, iflow_id: str, version: str = "active"):
    """Download an iFlow as a ZIP file from CPI design-time."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")
    url = f"{base}/IntegrationDesigntimeArtifacts(Id='{iflow_id}',Version='{version}')/$value"
    resp = httpx.get(url, headers=_headers(), auth=_auth(), timeout=60)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Export failed: {resp.text[:300]}")
    return StreamingResponse(
        _io_mod.BytesIO(resp.content),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{iflow_id}.zip"'},
    )


# ── Delete iFlow from design-time ─────────────────────────────────────────────

@router.delete("/packages/{package_id}/iflows/{iflow_id}")
def delete_iflow(package_id: str, iflow_id: str):
    """Delete an iFlow from design-time (does NOT undeploy from runtime)."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")
    headers = _csrf_write_headers(base)
    resp = httpx.delete(
        f"{base}/IntegrationDesigntimeArtifacts(Id='{iflow_id}',Version='active')",
        headers=headers, auth=_auth(), timeout=30,
    )
    if resp.status_code in (200, 202, 204):
        return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete iFlow failed: {resp.text[:300]}")


# ── Runtime status ────────────────────────────────────────────────────────────

@router.get("/runtime")
def list_runtime_artifacts():
    """Return all currently deployed runtime artifacts as a dict {id: status}."""
    try:
        data = _get("/IntegrationRuntimeArtifacts?$format=json")
        results = data.get("d", {}).get("results", [])
        return {r["Id"]: r.get("Status", "STARTED") for r in results}
    except Exception:
        return {}


@router.get("/runtime/{iflow_id}/status")
def get_runtime_status(iflow_id: str):
    """
    Get the current deployment status of a single iFlow, including error details.
    Returns: { status, error, deployedBy, deployedOn }
    Status values: STARTED | ERROR | STARTING | STOPPING | STOPPED
    """
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")

    # Get main artifact status
    artifact_url = f"{base}/IntegrationRuntimeArtifacts('{iflow_id}')?$format=json"
    resp = httpx.get(artifact_url, headers=_headers(), auth=_auth(), timeout=15)

    if resp.status_code == 404:
        return {"status": "NOT_DEPLOYED", "error": None}

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Status check failed: {resp.text[:200]}")

    artifact = resp.json().get("d", {})
    status = artifact.get("Status", "UNKNOWN")
    error_info = None

    # If ERROR, fetch the error information navigation property
    if status == "ERROR":
        try:
            err_resp = httpx.get(
                f"{base}/IntegrationRuntimeArtifacts('{iflow_id}')/ErrorInformation?$format=json",
                headers=_headers(), auth=_auth(), timeout=15,
            )
            if err_resp.status_code == 200:
                err_data = err_resp.json().get("d", {})
                error_info = err_data.get("Parameter") or err_data.get("Type") or "Deployment failed — check SAP Integration Suite logs."
        except Exception:
            error_info = "Deployment failed — check SAP Integration Suite logs."

    return {
        "status":      status,
        "error":       error_info,
        "deployedBy":  artifact.get("DeployedBy"),
        "deployedOn":  artifact.get("DeployedOn"),
        "version":     artifact.get("Version"),
    }


# ── iFlow deployment ──────────────────────────────────────────────────────────

@router.post("/packages/{package_id}/iflows/{iflow_id}/deploy")
def deploy_iflow(package_id: str, iflow_id: str):
    """Deploy (activate) a design-time iFlow to the runtime."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")
    url = f"{base}/DeployIntegrationDesigntimeArtifact?Id='{iflow_id}'&Version='active'"
    resp = httpx.post(url, headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202):
        task_id = None
        try:
            task_id = resp.json().get("d", {}).get("results", {}).get("TaskId")
        except Exception:
            pass
        return {"status": "deploying", "iflow": iflow_id, "taskId": task_id}
    raise HTTPException(resp.status_code, resp.text)


@router.delete("/runtime/{iflow_id}")
def undeploy_iflow(iflow_id: str):
    """Undeploy (stop) a runtime iFlow."""
    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set")
    # Need CSRF token from a runtime endpoint
    csrf_resp = httpx.get(
        f"{base}/IntegrationRuntimeArtifacts?$top=1&$format=json",
        headers={**_headers(), "X-CSRF-Token": "Fetch"},
        auth=_auth(), timeout=15,
    )
    token = csrf_resp.headers.get("x-csrf-token", "")
    del_headers = {**_headers(), "X-CSRF-Token": token}
    resp = httpx.delete(
        f"{base}/IntegrationRuntimeArtifacts('{iflow_id}')",
        headers=del_headers, auth=_auth(), timeout=30,
    )
    if resp.status_code in (200, 202, 204):
        return {"status": "undeployed", "iflow": iflow_id}
    raise HTTPException(resp.status_code, f"Undeploy failed: {resp.text[:300]}")


# ── Message monitoring ────────────────────────────────────────────────────────

@router.get("/messages")
def list_messages(top: int = 50, status: Optional[str] = None):
    """
    List recent message processing logs.
    status: COMPLETED | FAILED | PROCESSING | RETRY | CANCELLED
    """
    params = {"$format": "json", "$top": top, "$orderby": "LogStart desc"}
    if status:
        params["$filter"] = f"Status eq '{status}'"
    data = _get("/MessageProcessingLogs", params=params)
    results = data.get("d", {}).get("results", [])
    return [
        {
            "id":          m.get("MessageGuid"),
            "iflow":       m.get("IntegrationFlowName"),
            "status":      m.get("Status"),
            "start":       m.get("LogStart"),
            "end":         m.get("LogEnd"),
            "sender":      m.get("Sender"),
            "receiver":    m.get("Receiver"),
            "error":       m.get("CustomStatus"),
        }
        for m in results
    ]


@router.get("/messages/{message_guid}/error")
def get_message_error(message_guid: str):
    """Fetch the error information for a failed message."""
    try:
        data = _get(f"/MessageProcessingLogs('{message_guid}')/ErrorInformation?$format=json")
        result = data.get("d", {})
        return {
            "lastErrorModelStepId": result.get("LastErrorModelStepId"),
            "text": result.get("Text", ""),
        }
    except HTTPException as e:
        if e.status_code == 404:
            return {"text": "No error details available."}
        raise


# ── Security material (read-only metadata) ────────────────────────────────────

@router.get("/security/credentials")
def list_credentials():
    """List User Credential security artifacts."""
    data = _get("/UserCredentials?$format=json")
    results = data.get("d", {}).get("results", [])
    return [{"name": c.get("Name"), "kind": c.get("Kind"), "modified": c.get("ModifiedAt")} for c in results]


@router.get("/security/keystores")
def list_keystores():
    """List Keystore Entries."""
    data = _get("/KeystoreEntries?$format=json")
    results = data.get("d", {}).get("results", [])
    return [{"alias": k.get("Alias"), "type": k.get("Type")} for k in results]


# ── iFlow import ──────────────────────────────────────────────────────────────

class ImportIFlowRequest(BaseModel):
    package_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    xml: str
    scripts: dict = {}
    xsds: dict = {}
    mmaps: dict = {}


@router.post("/import-iflow")
def import_iflow(req: ImportIFlowRequest):
    """
    Build a CPI-importable ZIP from the generated iFlow and push it to a
    design-time package via the CPI OData API.
    Creates the artifact if it doesn't exist; updates (PUT) if it does (409).
    """
    from services.iflow_packager import build_iflow_zip

    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set in backend/.env")

    # 1. Build the ZIP bundle
    zip_bytes = build_iflow_zip(
        iflow_xml=req.xml,
        name=req.name,
        description=req.description,
        version=req.version,
        scripts=req.scripts or {},
        xsds=req.xsds or {},
        mmaps=req.mmaps or {},
    )
    artifact_content = _b64.b64encode(zip_bytes).decode()

    # 2. Derive a CPI-valid artifact ID: only [A-Za-z0-9_], must not start with digit
    iflow_id = re.sub(r"[^A-Za-z0-9_]", "_", req.name.strip())
    iflow_id = re.sub(r"_+", "_", iflow_id).strip("_")
    if iflow_id and iflow_id[0].isdigit():
        iflow_id = "_" + iflow_id
    iflow_id = iflow_id or "MyIFlow"

    # 3. Fetch CSRF token (CPI requires it for all write operations)
    csrf_resp = httpx.get(
        f"{base}/IntegrationDesigntimeArtifacts?$top=1&$format=json",
        headers={**_headers(), "X-CSRF-Token": "Fetch"},
        auth=_auth(),
        timeout=15,
    )
    csrf_token = csrf_resp.headers.get("x-csrf-token", "")

    write_headers = {
        **_headers(),
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf_token,
        "Accept": "application/json",
    }

    # NOTE: "Version" must NOT be in the POST body — CPI auto-assigns it on create.
    body = {
        "PackageId": req.package_id,
        "Name": req.name,
        "Id": iflow_id,
        "ArtifactContent": artifact_content,
        "Description": req.description,
    }

    # 4a. Try POST (create new artifact)
    resp = httpx.post(
        f"{base}/IntegrationDesigntimeArtifacts",
        headers=write_headers,
        auth=_auth(),
        json=body,
        timeout=30,
    )

    if resp.status_code in (200, 201):
        return {"status": "imported", "id": iflow_id, "package": req.package_id}

    # 4b. 409 Conflict → artifact already exists, update it
    if resp.status_code == 409:
        put_resp = httpx.put(
            f"{base}/IntegrationDesigntimeArtifacts(Id='{iflow_id}',Version='active')",
            headers=write_headers,
            auth=_auth(),
            json={
                "ArtifactContent": artifact_content,
                "Name": req.name,
                "Version": req.version,
            },
            timeout=30,
        )
        if put_resp.status_code in (200, 201, 202, 204):
            return {"status": "updated", "id": iflow_id, "package": req.package_id}
        raise HTTPException(put_resp.status_code, f"Update failed: {put_resp.text[:500]}")

    raise HTTPException(resp.status_code, f"Import failed: {resp.text[:500]}")


# ── Artifact type → CPI OData entity mapping ─────────────────────────────────

_ARTIFACT_ENTITY: dict[str, str] = {
    "iflow":            "IntegrationDesigntimeArtifacts",
    "messagemapping":   "MessageMappingDesigntimeArtifacts",
    "valuemapping":     "ValueMappingDesigntimeArtifacts",
    "scriptcollection": "ScriptCollectionDesigntimeArtifacts",
    "functionlibrary":  "FunctionLibraryDesigntimeArtifacts",
    "restapi":          "RestApiDesigntimeArtifacts",
    "soapapi":          "SoapApiDesigntimeArtifacts",
    "odataapi":         "OdataDesigntimeArtifacts",
}

def _entity_for(artifact_type: str) -> str:
    return _ARTIFACT_ENTITY.get(artifact_type.lower().replace(" ", "").replace("_", ""),
                                 "IntegrationDesigntimeArtifacts")


# ── Import artifact ZIP (any type) ───────────────────────────────────────────

@router.post("/import-zip")
async def import_zip_file(
    file:          UploadFile = File(...),
    package_id:    str        = Form(...),
    artifact_type: str        = Form("iflow"),
    artifact_id:   str        = Form(""),    # optional override
    artifact_name: str        = Form(""),    # optional override
):
    """
    Import a SAP CPI artifact ZIP into a package.
    Supports: iflow, messagemapping, valuemapping, scriptcollection,
              functionlibrary, restapi, soapapi, odataapi.
    Reads metadata from the ZIP when possible; falls back to filename.
    Creates the artifact if new; PUT-updates if it already exists (409).
    """
    import zipfile
    import io as _io

    base = _api_base()
    if not base:
        raise HTTPException(503, "CPI_API_BASE_URL not set in backend/.env")

    zip_bytes = await file.read()
    entity    = _entity_for(artifact_type)

    # ── Extract metadata from the ZIP ────────────────────────────────────────
    art_id      = artifact_id.strip()
    art_name    = artifact_name.strip()
    version     = "1.0.0"
    description = ""

    try:
        with zipfile.ZipFile(_io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()

            # iFlow ID from .iflw filename
            if not art_id:
                iflw = [n for n in names if n.endswith(".iflw")]
                if iflw:
                    art_id = iflw[0].split("/")[-1].replace(".iflw", "")

            # Message Mapping ID from .mmap filename
            if not art_id:
                mmaps = [n for n in names if n.endswith(".mmap")]
                if mmaps:
                    art_id = mmaps[0].split("/")[-1].replace(".mmap", "")

            # Name from .project
            if not art_name and ".project" in names:
                proj = zf.read(".project").decode("utf-8", errors="replace")
                m = re.search(r"<name>([^<]+)</name>", proj)
                if m:
                    art_name = m.group(1).strip()

            # Version from MANIFEST.MF
            if "META-INF/MANIFEST.MF" in names:
                manifest = zf.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace")
                m = re.search(r"Bundle-Version:\s*([^\r\n]+)", manifest)
                if m:
                    version = m.group(1).strip()

            # Description from metainfo.prop
            if "metainfo.prop" in names:
                metainfo = zf.read("metainfo.prop").decode("utf-8", errors="replace")
                m = re.search(r"description=(.+)", metainfo)
                if m:
                    description = m.group(1).strip()

    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid ZIP file.")

    # Fallback: derive from filename
    if not art_id:
        art_id = re.sub(r"\.(zip|mmap)$", "", file.filename or "artifact", flags=re.I)

    # Sanitize ID
    art_id = re.sub(r"[^A-Za-z0-9_]", "_", art_id)
    art_id = re.sub(r"_+", "_", art_id).strip("_")
    if art_id and art_id[0].isdigit():
        art_id = "_" + art_id
    art_id   = art_id or "MyArtifact"
    art_name = art_name or art_id

    # ── Prepare artifact content ───────────────────────────────────────────────
    # Per official SAP spec (IntegrationContent.json): ArtifactContent is
    # "message mapping zip content in base64-encoded format".
    # The PUT description says CPI reads bundle version/name from MANIFEST.MF,
    # so the ZIP must contain META-INF/MANIFEST.MF for API upload.
    # Real CPI export ZIPs don't have the manifest (UI import is more lenient)
    # but the API requires it.
    import zipfile as _zf, io as _io
    if artifact_type.lower() == "messagemapping":
        try:
            with _zf.ZipFile(_io.BytesIO(zip_bytes)) as zf:
                existing = zf.namelist()
                # Extract .mmap name for use as artifact ID/name if not set
                mmap_files = [n for n in existing if n.endswith(".mmap")]
                if mmap_files:
                    extracted = mmap_files[0].split("/")[-1].replace(".mmap", "")
                    if extracted and not art_name:
                        art_name = extracted
                    if extracted and not art_id:
                        art_id = re.sub(r"[^A-Za-z0-9_]", "_", extracted)

                # Inject MANIFEST.MF if missing (required by CPI API)
                if "META-INF/MANIFEST.MF" not in existing:
                    buf = _io.BytesIO()
                    manifest_txt = (
                        "Manifest-Version: 1.0\r\n"
                        f"Bundle-SymbolicName: {art_id}\r\n"
                        f"Bundle-Name: {art_name}\r\n"
                        f"Bundle-Version: {version}\r\n"
                        "\r\n"
                    )
                    with _zf.ZipFile(buf, "w", _zf.ZIP_DEFLATED) as out:
                        out.writestr("META-INF/MANIFEST.MF", manifest_txt.encode())
                        for item in zf.infolist():
                            out.writestr(item, zf.read(item.filename))
                    zip_bytes = buf.getvalue()
        except Exception:
            pass

    artifact_content = _b64.b64encode(zip_bytes).decode()

    # ── Fetch CSRF token ──────────────────────────────────────────────────────
    csrf_resp = httpx.get(
        f"{base}/{entity}?$top=1&$format=json",
        headers={**_headers(), "X-CSRF-Token": "Fetch"},
        auth=_auth(), timeout=15,
    )
    csrf_token = csrf_resp.headers.get("x-csrf-token", "")
    write_headers = {
        **_headers(),
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf_token,
        "Accept": "application/json",
    }

    body = {
        "PackageId":       package_id,
        "Name":            art_name,
        "Id":              art_id,
        "ArtifactContent": artifact_content,
        "Description":     description,
    }

    # ── POST (create) ─────────────────────────────────────────────────────────
    # Per official SAP spec: POST to flat /MessageMappingDesigntimeArtifacts
    # (not the package-scoped navigation path — that is GET only per spec)
    resp = httpx.post(
        f"{base}/{entity}",
        headers=write_headers, auth=_auth(), json=body, timeout=60,
    )

    if resp.status_code in (200, 201):
        return {"status": "imported", "id": art_id, "name": art_name,
                "package": package_id, "type": artifact_type}

    # ── 409 → already exists → update ────────────────────────────────────────
    if resp.status_code == 409:
        put_resp = httpx.put(
            f"{base}/{entity}(Id='{art_id}',Version='active')",
            headers=write_headers, auth=_auth(),
            json={"ArtifactContent": artifact_content, "Name": art_name, "Version": version},
            timeout=60,
        )
        if put_resp.status_code in (200, 201, 202, 204):
            return {"status": "updated", "id": art_id, "name": art_name,
                    "package": package_id, "type": artifact_type}
        raise HTTPException(put_resp.status_code, f"Update failed: {put_resp.text[:500]}")

    raise HTTPException(resp.status_code, f"Import failed: {resp.text[:500]}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED CPI API COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

# ── Package update ────────────────────────────────────────────────────────────

class UpdatePackageRequest(BaseModel):
    name: str
    description: str = ""

@router.put("/packages/{package_id}")
def update_package(package_id: str, req: UpdatePackageRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    headers = _csrf_write_headers(base)
    resp = httpx.put(f"{base}/IntegrationPackages('{package_id}')", headers=headers, auth=_auth(),
                     json={"Name": req.name, "Description": req.description, "ShortText": req.description}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated"}
    raise HTTPException(resp.status_code, f"Update package failed: {resp.text[:300]}")


# ── All artifact types in a package ──────────────────────────────────────────

@router.get("/packages/{package_id}/all-artifacts")
def list_all_artifacts(package_id: str):
    def _fetch(path: str, atype: str) -> list:
        try:
            return [{"id": a.get("Id"), "name": a.get("Name"), "version": a.get("Version"), "artifactType": atype}
                    for a in _get(path).get("d", {}).get("results", [])]
        except Exception:
            return []
    return {
        "iflows":            _fetch(f"/IntegrationPackages('{package_id}')/IntegrationDesigntimeArtifacts?$format=json", "iflow"),
        "valueMappings":     _fetch(f"/IntegrationPackages('{package_id}')/ValueMappingDesigntimeArtifacts?$format=json", "valueMapping"),
        "scriptCollections": _fetch(f"/IntegrationPackages('{package_id}')/ScriptCollectionDesigntimeArtifacts?$format=json", "scriptCollection"),
    }


# ── Externalized Parameters ───────────────────────────────────────────────────

@router.get("/iflows/{iflow_id}/configurations")
def list_configurations(iflow_id: str):
    try:
        data = _get(f"/IntegrationDesigntimeArtifactConfigurations(Id='{iflow_id}',Version='active')?$format=json")
        return [{"key": c.get("ParameterKey"), "value": c.get("ParameterValue"),
                 "dataType": c.get("DataType"), "description": c.get("Description", "")}
                for c in data.get("d", {}).get("results", [])]
    except HTTPException as e:
        if e.status_code == 404: return []
        raise


class UpdateConfigRequest(BaseModel):
    value: str

@router.put("/iflows/{iflow_id}/configurations/{param_key}")
def update_configuration(iflow_id: str, param_key: str, req: UpdateConfigRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    headers = _csrf_write_headers(base)
    resp = httpx.put(
        f"{base}/IntegrationDesigntimeArtifactConfigurations(Id='{iflow_id}',Version='active',ParameterKey='{param_key}')",
        headers=headers, auth=_auth(), json={"ParameterValue": req.value}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated", "key": param_key, "value": req.value}
    raise HTTPException(resp.status_code, f"Update config failed: {resp.text[:300]}")


# ── Copy iFlow between packages ───────────────────────────────────────────────

class CopyIflowRequest(BaseModel):
    source_id:         str
    target_package_id: str
    new_name:          Optional[str] = None

@router.post("/copy-iflow")
def copy_iflow(req: CopyIflowRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    exp = httpx.get(f"{base}/IntegrationDesigntimeArtifacts(Id='{req.source_id}',Version='active')/$value",
                    headers=_headers(), auth=_auth(), timeout=60)
    if exp.status_code != 200: raise HTTPException(exp.status_code, f"Export failed: {exp.text[:200]}")
    new_name = req.new_name or req.source_id
    new_id   = re.sub(r"[^A-Za-z0-9_]", "_", new_name.strip())
    new_id   = re.sub(r"_+", "_", new_id).strip("_") or "CopiedIFlow"
    if new_id[0].isdigit(): new_id = "_" + new_id
    resp = httpx.post(f"{base}/IntegrationDesigntimeArtifacts", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"PackageId": req.target_package_id, "Name": new_name, "Id": new_id,
                            "ArtifactContent": _b64.b64encode(exp.content).decode()}, timeout=60)
    if resp.status_code in (200, 201): return {"status": "copied", "id": new_id, "name": new_name}
    if resp.status_code == 409: raise HTTPException(409, f"'{new_id}' already exists in target package — choose a different name.")
    raise HTTPException(resp.status_code, f"Copy failed: {resp.text[:300]}")


# ── Bulk deploy ───────────────────────────────────────────────────────────────

@router.post("/packages/{package_id}/deploy-all")
def deploy_all_iflows(package_id: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    iflows   = _get(f"/IntegrationPackages('{package_id}')/IntegrationDesigntimeArtifacts?$format=json").get("d", {}).get("results", [])
    deployed, errors = [], []
    for iflow in iflows:
        iid = iflow.get("Id")
        try:
            r = httpx.post(f"{base}/DeployIntegrationDesigntimeArtifact?Id='{iid}'&Version='active'",
                           headers=_headers(), auth=_auth(), timeout=30)
            if r.status_code in (200, 202): deployed.append(iid)
            else: errors.append({"id": iid, "error": r.text[:200]})
        except Exception as e: errors.append({"id": iid, "error": str(e)})
    return {"deployed": deployed, "errors": errors, "total": len(iflows)}


# ── Data Stores ───────────────────────────────────────────────────────────────

@router.get("/datastores")
def list_datastores():
    try:
        results = _get("/DataStores?$format=json").get("d", {}).get("results", [])
        return [{"name": d.get("DataStoreName"), "type": d.get("Type"), "visibility": d.get("Visibility"),
                 "messages": d.get("NumberOfMessages", 0), "overdue": d.get("NumberOfOverdueMessages", 0)} for d in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise

@router.get("/datastores/{name}/entries")
def list_datastore_entries(name: str, top: int = 50):
    try:
        results = _get("/DataStoreEntries", params={"$format": "json", "$filter": f"DataStoreName eq '{name}'",
                       "$top": top, "$orderby": "DueAt desc"}).get("d", {}).get("results", [])
        return [{"id": e.get("Id"), "messageId": e.get("MessageId"), "status": e.get("Status"),
                 "dueAt": e.get("DueAt"), "retries": e.get("Retries", 0)} for e in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise

@router.delete("/datastores/{name}/entries/{entry_id}")
def delete_datastore_entry(name: str, entry_id: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/DataStoreEntries(Id='{entry_id}',DataStoreName='{name}')",
                        headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete entry failed: {resp.text[:200]}")


# ── Security — extended ───────────────────────────────────────────────────────

@router.get("/security/secure-parameters")
def list_secure_parameters():
    try:
        results = _get("/SecureParameters?$format=json").get("d", {}).get("results", [])
        return [{"name": p.get("Name"), "description": p.get("Description", ""), "modified": p.get("ModifiedAt")} for p in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise

@router.get("/security/oauth-credentials")
def list_oauth_credentials():
    try:
        results = _get("/OAuthClientCredentials?$format=json").get("d", {}).get("results", [])
        return [{"name": o.get("Name"), "clientId": o.get("ClientId"),
                 "tokenServiceUrl": o.get("TokenServiceUrl"), "modified": o.get("ModifiedAt")} for o in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise

@router.get("/security/certificate-mappings")
def list_certificate_mappings():
    try:
        results = _get("/CertificateUserMappings?$format=json").get("d", {}).get("results", [])
        return [{"id": c.get("Id"), "user": c.get("User"), "validUntil": c.get("ValidUntil")} for c in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise


# ── Number Ranges ─────────────────────────────────────────────────────────────

@router.get("/number-ranges")
def list_number_ranges():
    try:
        results = _get("/NumberRanges?$format=json").get("d", {}).get("results", [])
        return [{"name": n.get("Name"), "description": n.get("Description", ""),
                 "min": n.get("MinValue"), "max": n.get("MaxValue"), "current": n.get("CurrentValue"),
                 "fieldLength": n.get("FieldLength"), "rotate": n.get("Rotate"), "modified": n.get("ModifiedAt")}
                for n in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise


# ── Log Files ─────────────────────────────────────────────────────────────────

@router.get("/log-files")
def list_log_files():
    try:
        results = _get("/LogFiles?$format=json").get("d", {}).get("results", [])
        return [{"name": f.get("Name"), "application": f.get("Application"),
                 "lastModified": f.get("LastModified"), "contentType": f.get("ContentType")} for f in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise


# ── Message Processing Log — runs & attachments ───────────────────────────────

@router.get("/messages/{message_guid}/runs")
def get_message_runs(message_guid: str):
    try:
        results = _get(f"/MessageProcessingLogs('{message_guid}')/MessageProcessingLogRuns?$format=json").get("d", {}).get("results", [])
        return [{"status": r.get("Status"), "start": r.get("RunStart"), "stop": r.get("RunStop"),
                 "processingNode": r.get("ProcessingNode"), "stepId": r.get("ModelStepId")} for r in results]
    except HTTPException as e:
        if e.status_code == 404: return []
        raise

@router.get("/messages/{message_guid}/attachments")
def get_message_attachments(message_guid: str):
    try:
        results = _get(f"/MessageProcessingLogs('{message_guid}')/MessageProcessingLogAttachments?$format=json").get("d", {}).get("results", [])
        return [{"id": a.get("Id"), "name": a.get("Name"), "contentType": a.get("ContentType"), "timeStamp": a.get("TimeStamp")} for a in results]
    except HTTPException as e:
        if e.status_code == 404: return []
        raise


# ── Message Store Entries ─────────────────────────────────────────────────────

@router.get("/message-store-entries")
def list_message_store_entries(top: int = 20):
    try:
        results = _get("/MessageStoreEntries", params={"$format": "json", "$top": top}).get("d", {}).get("results", [])
        return [{"id": e.get("Id"), "messageId": e.get("MessageId"), "status": e.get("Status"),
                 "due": e.get("DueAt"), "retries": e.get("Retries")} for e in results]
    except HTTPException as e:
        if e.status_code in (404, 403): return []
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED API — Round 2
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_list(path: str, mapper, params: dict | None = None) -> list:
    """
    Calls _get(path) and maps results with mapper.
    Returns [] gracefully for any CPI error (404, 403, 400, 500, etc.)
    so trial/restricted tenants don't cause frontend 500s.
    """
    try:
        results = _get(path, params=params).get("d", {}).get("results", [])
        return [mapper(r) for r in results]
    except (HTTPException, httpx.HTTPStatusError, httpx.RequestError, Exception):
        return []

# ── Variables (runtime iFlow variables — "String Parameters") ─────────────────

@router.get("/variables")
def list_variables():
    """List all runtime variables written by iFlows (Write Variable step)."""
    return _safe_list("/Variables?$format=json", lambda v: {
        "name": v.get("VariableName"), "iflow": v.get("IntegrationFlow"),
        "visibility": v.get("Visibility"), "updatedAt": v.get("UpdatedAt"),
    })

@router.delete("/variables/{iflow_id}/{var_name}")
def delete_variable(iflow_id: str, var_name: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(
        f"{base}/Variables(VariableName='{var_name}',IntegrationFlow='{iflow_id}')",
        headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete variable failed: {resp.text[:200]}")


# ── Tenant-level Configurations (global string parameters) ────────────────────

@router.get("/tenant-configurations")
def list_tenant_configurations():
    """List tenant-level configuration parameters (global key-value settings)."""
    return _safe_list("/Configurations?$format=json", lambda c: {
        "key": c.get("ParameterKey"), "value": c.get("ParameterValue"), "dataType": c.get("DataType"),
    })

class TenantConfigRequest(BaseModel):
    value: str

@router.put("/tenant-configurations/{param_key}")
def update_tenant_configuration(param_key: str, req: TenantConfigRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.put(f"{base}/Configurations(ParameterKey='{param_key}')",
                     headers=_csrf_write_headers(base), auth=_auth(),
                     json={"ParameterValue": req.value}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated"}
    raise HTTPException(resp.status_code, f"Update tenant config failed: {resp.text[:300]}")


# ── Build & Deploy Status (async task polling) ────────────────────────────────

@router.get("/deploy-status/{task_id}")
def get_deploy_status(task_id: str):
    """Poll async deployment task. CPI deploy returns a TaskId; use this to track completion."""
    try:
        data = _get(f"/BuildAndDeployStatus(TaskId='{task_id}')?$format=json")
        d = data.get("d", {})
        return {"taskId": task_id, "status": d.get("Status"),
                "deployedArtifactId": d.get("DeployedArtifactId"),
                "message": d.get("DeployedArtifactVersion")}
    except Exception:
        return {"taskId": task_id, "status": "UNKNOWN"}


# ── Message Adapter Attributes ─────────────────────────────────────────────────

@router.get("/messages/{message_guid}/adapter-attributes")
def get_message_adapter_attributes(message_guid: str):
    """Get adapter-level attributes (channel, connector, headers) for a message processing log."""
    return _safe_list(
        f"/MessageProcessingLogs('{message_guid}')/AdapterAttributes?$format=json",
        lambda a: {"name": a.get("Name"), "value": a.get("Value"), "adapterName": a.get("AdapterName")},
    )


# ── Log file download ─────────────────────────────────────────────────────────

@router.get("/log-files/{application}/download")
def download_log_file(application: str):
    """Download latest log archive for a given application as a ZIP/stream."""
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.get(
        f"{base}/LogFileArchives(Application='{application}',LogFileType='Application',NodeScope='%27%27')/$value",
        headers=_headers(), auth=_auth(), timeout=60)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Log download failed: {resp.text[:200]}")
    ct = resp.headers.get("content-type", "application/zip")
    return StreamingResponse(_io_mod.BytesIO(resp.content), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="{application}_logs.zip"'})


# ── Data Store Entry payload download ─────────────────────────────────────────

@router.get("/datastores/{store_name}/entries/{entry_id}/payload")
def download_datastore_entry_payload(store_name: str, entry_id: str):
    """Download the actual message payload stored in a data store entry."""
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.get(
        f"{base}/DataStoreEntries(Id='{entry_id}',DataStoreName='{store_name}',IntegrationFlow='')/$value",
        headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code != 200:
        # Try without IntegrationFlow key
        resp = httpx.get(
            f"{base}/DataStoreEntries(Id='{entry_id}',DataStoreName='{store_name}')/$value",
            headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Payload download failed: {resp.text[:200]}")
    ct = resp.headers.get("content-type", "application/xml")
    return StreamingResponse(_io_mod.BytesIO(resp.content), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="entry_{entry_id}.xml"'})


# ── Message Store Entry payload + attachments ─────────────────────────────────

@router.get("/message-store-entries/{entry_id}/payload")
def download_message_store_entry_payload(entry_id: str):
    """Download the message payload from a message store entry."""
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.get(f"{base}/MessageStoreEntries('{entry_id}')/$value",
                     headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Payload download failed: {resp.text[:200]}")
    ct = resp.headers.get("content-type", "application/xml")
    return StreamingResponse(_io_mod.BytesIO(resp.content), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="msg_{entry_id}.xml"'})

@router.get("/message-store-entries/{entry_id}/attachments")
def list_message_store_entry_attachments(entry_id: str):
    return _safe_list(
        f"/MessageStoreEntries('{entry_id}')/Attachments?$format=json",
        lambda a: {"id": a.get("Id"), "name": a.get("Name"), "contentType": a.get("ContentType")},
    )

@router.get("/message-store-entries/{entry_id}/attachments/{attachment_id}/payload")
def download_message_store_attachment(entry_id: str, attachment_id: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.get(
        f"{base}/MessageStoreEntries('{entry_id}')/Attachments('{attachment_id}')/$value",
        headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Attachment download failed: {resp.text[:200]}")
    ct = resp.headers.get("content-type", "application/octet-stream")
    return StreamingResponse(_io_mod.BytesIO(resp.content), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="attachment_{attachment_id}"'})


# ── Security — User Credentials CRUD ─────────────────────────────────────────

class CredentialRequest(BaseModel):
    name: str
    username: str
    password: str
    kind: str = "default"
    description: str = ""

@router.post("/security/credentials")
def create_credential(req: CredentialRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.post(f"{base}/UserCredentials", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"Name": req.name, "User": req.username, "Password": req.password,
                            "Kind": req.kind, "Description": req.description}, timeout=30)
    if resp.status_code in (200, 201): return {"status": "created", "name": req.name}
    raise HTTPException(resp.status_code, f"Create credential failed: {resp.text[:300]}")

class UpdateCredentialRequest(BaseModel):
    username: str
    password: str
    description: str = ""

@router.put("/security/credentials/{name}")
def update_credential(name: str, req: UpdateCredentialRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.put(f"{base}/UserCredentials('{name}')", headers=_csrf_write_headers(base), auth=_auth(),
                     json={"User": req.username, "Password": req.password, "Description": req.description}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated"}
    raise HTTPException(resp.status_code, f"Update credential failed: {resp.text[:300]}")

@router.delete("/security/credentials/{name}")
def delete_credential(name: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/UserCredentials('{name}')", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete credential failed: {resp.text[:300]}")


# ── Security — Secure Parameters CRUD ────────────────────────────────────────

class SecureParamRequest(BaseModel):
    name: str
    value: str
    description: str = ""

@router.post("/security/secure-parameters")
def create_secure_parameter(req: SecureParamRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.post(f"{base}/SecureParameters", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"Name": req.name, "SecureParam": req.value, "Description": req.description}, timeout=30)
    if resp.status_code in (200, 201): return {"status": "created", "name": req.name}
    raise HTTPException(resp.status_code, f"Create secure parameter failed: {resp.text[:300]}")

class UpdateSecureParamRequest(BaseModel):
    value: str
    description: str = ""

@router.put("/security/secure-parameters/{name}")
def update_secure_parameter(name: str, req: UpdateSecureParamRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.put(f"{base}/SecureParameters('{name}')", headers=_csrf_write_headers(base), auth=_auth(),
                     json={"SecureParam": req.value, "Description": req.description}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated"}
    raise HTTPException(resp.status_code, f"Update secure parameter failed: {resp.text[:300]}")

@router.delete("/security/secure-parameters/{name}")
def delete_secure_parameter(name: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/SecureParameters('{name}')", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete secure parameter failed: {resp.text[:300]}")


# ── Security — OAuth Client Credentials CRUD ──────────────────────────────────

class OAuthCredRequest(BaseModel):
    name: str
    clientId: str
    clientSecret: str
    tokenServiceUrl: str
    scope: str = ""
    description: str = ""

@router.post("/security/oauth-credentials")
def create_oauth_credential(req: OAuthCredRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.post(f"{base}/OAuthClientCredentials", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"Name": req.name, "ClientId": req.clientId, "ClientSecret": req.clientSecret,
                            "TokenServiceUrl": req.tokenServiceUrl, "Scope": req.scope,
                            "Description": req.description}, timeout=30)
    if resp.status_code in (200, 201): return {"status": "created", "name": req.name}
    raise HTTPException(resp.status_code, f"Create OAuth credential failed: {resp.text[:300]}")

@router.delete("/security/oauth-credentials/{name}")
def delete_oauth_credential(name: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/OAuthClientCredentials('{name}')", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete OAuth credential failed: {resp.text[:300]}")


# ── Security — Number Ranges CRUD ─────────────────────────────────────────────

class NumberRangeRequest(BaseModel):
    name: str
    description: str = ""
    minValue: str = "1"
    maxValue: str = "99999999"
    currentValue: str = "1"
    fieldLength: str = "10"
    rotate: bool = False

@router.post("/security/number-ranges")
def create_number_range(req: NumberRangeRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.post(f"{base}/NumberRanges", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"Name": req.name, "Description": req.description, "MinValue": req.minValue,
                            "MaxValue": req.maxValue, "CurrentValue": req.currentValue,
                            "FieldLength": req.fieldLength, "Rotate": req.rotate}, timeout=30)
    if resp.status_code in (200, 201): return {"status": "created", "name": req.name}
    raise HTTPException(resp.status_code, f"Create number range failed: {resp.text[:300]}")

@router.put("/security/number-ranges/{name}")
def update_number_range(name: str, req: NumberRangeRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.put(f"{base}/NumberRanges('{name}')", headers=_csrf_write_headers(base), auth=_auth(),
                     json={"Description": req.description, "MinValue": req.minValue, "MaxValue": req.maxValue,
                           "CurrentValue": req.currentValue, "FieldLength": req.fieldLength,
                           "Rotate": req.rotate}, timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "updated"}
    raise HTTPException(resp.status_code, f"Update number range failed: {resp.text[:300]}")

@router.delete("/security/number-ranges/{name}")
def delete_number_range(name: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/NumberRanges('{name}')", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete number range failed: {resp.text[:300]}")


# ── Access Policies ───────────────────────────────────────────────────────────

@router.get("/access-policies")
def list_access_policies():
    return _safe_list("/AccessPolicies?$format=json", lambda p: {
        "id": p.get("Id"), "roleName": p.get("RoleName"), "description": p.get("Description"),
    })

class AccessPolicyRequest(BaseModel):
    roleName: str
    description: str = ""

@router.post("/access-policies")
def create_access_policy(req: AccessPolicyRequest):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.post(f"{base}/AccessPolicies", headers=_csrf_write_headers(base), auth=_auth(),
                      json={"RoleName": req.roleName, "Description": req.description}, timeout=30)
    if resp.status_code in (200, 201):
        d = resp.json().get("d", {})
        return {"status": "created", "id": d.get("Id"), "roleName": req.roleName}
    raise HTTPException(resp.status_code, f"Create access policy failed: {resp.text[:300]}")

@router.delete("/access-policies/{policy_id}")
def delete_access_policy(policy_id: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/AccessPolicies({policy_id})", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete access policy failed: {resp.text[:300]}")

@router.get("/access-policies/{policy_id}/references")
def list_access_policy_references(policy_id: str):
    return _safe_list(
        f"/AccessPolicies({policy_id})/ArtifactReferences?$format=json",
        lambda r: {"id": r.get("Id"), "name": r.get("Name"), "type": r.get("Type")},
    )


# ── JMS Brokers ───────────────────────────────────────────────────────────────

@router.get("/jms-brokers")
def list_jms_brokers():
    """List JMS broker status and capacity (Advanced Event Mesh)."""
    return _safe_list("/JMSBrokers?$format=json", lambda b: {
        "name": b.get("Name"), "status": b.get("Status"),
        "queueCount": b.get("QueueCount"), "maxCapacity": b.get("MaxCapacity"),
        "capacityOk": b.get("IsCapacityOk"),
    })


# ── ID Mapper ─────────────────────────────────────────────────────────────────

@router.get("/id-maps")
def list_id_maps(agency: Optional[str] = None, scheme: Optional[str] = None):
    """List ID mapping entries (IdMapToIds)."""
    params: dict = {"$format": "json"}
    filters = []
    if agency: filters.append(f"SourceAgency eq '{agency}'")
    if scheme: filters.append(f"SourceScheme eq '{scheme}'")
    if filters: params["$filter"] = " and ".join(filters)
    return _safe_list("/IdMapToIds", lambda r: {
        "id": r.get("Id"), "sourceAgency": r.get("SourceAgency"),
        "sourceScheme": r.get("SourceScheme"), "sourceId": r.get("SourceId"),
        "targetAgency": r.get("TargetAgency"), "targetScheme": r.get("TargetScheme"),
        "targetId": r.get("TargetId"),
    }, params=params)

@router.delete("/id-maps/{map_id}")
def delete_id_map(map_id: str):
    base = _api_base()
    if not base: raise HTTPException(503, "CPI_API_BASE_URL not set")
    resp = httpx.delete(f"{base}/IdMapToIds('{map_id}')", headers=_csrf_write_headers(base), auth=_auth(), timeout=30)
    if resp.status_code in (200, 202, 204): return {"status": "deleted"}
    raise HTTPException(resp.status_code, f"Delete ID map failed: {resp.text[:200]}")
