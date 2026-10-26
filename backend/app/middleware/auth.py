import secrets
from typing import Optional
import uuid
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config.settings import settings

security_bearer = HTTPBearer(auto_error=False)


def get_current_client_identity(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    """
    Validates API authentication when API_AUTH_ENABLED=True.
    Supports either Authorization: Bearer <key> or X-API-Key: <key>.
    When API_AUTH_ENABLED=False (default for local development and initial testing),
    returns an anonymous developer identity.
    """
    if not settings.API_AUTH_ENABLED:
        return "developer_default"

    configured_key = settings.API_AUTH_KEY
    if not configured_key:
        # If auth is enabled but no key configured on the server, reject with 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication is enabled but API_AUTH_KEY is not configured.",
        )

    provided_token = None
    if auth_header and auth_header.credentials:
        provided_token = auth_header.credentials.strip()
    elif x_api_key and x_api_key.strip():
        provided_token = x_api_key.strip()

    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide 'Authorization: Bearer <token>' or 'X-API-Key: <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing side-channel attacks
    if not secrets.compare_digest(provided_token, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return "authenticated_user"


def verify_project_authorization(
    project_id: uuid.UUID,
    client_identity: str = Security(get_current_client_identity),
) -> bool:
    """
    Project-level authorization hook.
    In multi-tenant deployments, this ensures the client identity is authorized
    to view, modify, or execute tasks on the specified project_id.
    """
    # Reserved for future fine-grained role-based access control (RBAC).
    # Currently verifies valid authentication when enabled.
    return True
