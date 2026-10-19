from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.services.tools.registry import TOOL_REGISTRY, execute_tool, ToolDefinition
from app.services.tools.ssrf_guard import validate_url_safety

router = APIRouter(prefix="/tools", tags=["Live Data Tools & Integrations"])


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = {}
    idempotency_key: Optional[str] = None


class CustomHttpToolRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    body: Optional[Dict[str, Any]] = None
    timeout_seconds: float = 5.0


@router.get("", response_model=List[ToolDefinition])
def list_available_tools(ctx: TenantContext = Depends(get_tenant_context)):
    """Lists all registered tools and their input parameter schemas."""
    return [entry["definition"] for entry in TOOL_REGISTRY.values()]


@router.post("/execute")
def execute_registered_tool(
    req: ToolExecuteRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Executes an approved business tool with parameters, logging write actions in the tenant audit trail.
    """
    result = execute_tool(
        tool_name=req.tool_name,
        parameters=req.parameters,
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        db=db,
        idempotency_key=req.idempotency_key
    )
    return result


@router.post("/custom-http-test")
async def test_custom_http_tool(
    req: CustomHttpToolRequest,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Executes a test HTTP request to an external CRM or webhook with strict SSRF validation.
    Prevents access to private RFC1918, localhost, and cloud metadata.
    """
    # 1. SSRF Safety Verification
    validate_url_safety(req.url)

    # 2. Execute Request safely
    async with httpx.AsyncClient(timeout=req.timeout_seconds) as client:
        try:
            if req.method.upper() == "POST":
                resp = await client.post(req.url, headers=req.headers, json=req.body)
            elif req.method.upper() == "PUT":
                resp = await client.put(req.url, headers=req.headers, json=req.body)
            else:
                resp = await client.get(req.url, headers=req.headers)

            return {
                "status": "success",
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "data": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
            }
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"External request failed: {str(e)}")
