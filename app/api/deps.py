from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.services import auth_service

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    username: Optional[str] = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = await auth_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if current_user.get("account_status") != "active":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_websocket(
    websocket: WebSocket
) -> Optional[Dict[str, Any]]:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    username: Optional[str] = payload.get("sub")
    if username is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    user = await auth_service.get_user_by_username(username)
    if user is None or user.get("account_status") != "active":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Dict[str, Any] = Depends(get_current_active_user)):
        if current_user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
