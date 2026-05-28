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
import time
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

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
        return {"status": "deploying", "iflow": iflow_id}
    raise HTTPException(resp.status_code, resp.text)


# ── Message monitoring ────────────────────────────────────────────────────────

@router.get("/messages")
def list_messages(top: int = 20, status: Optional[str] = None):
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
        }
        for m in results
    ]


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
