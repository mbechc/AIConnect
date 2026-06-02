from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


bearer = HTTPBearer(auto_error=False)


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    if credentials.credentials != settings.api_admin_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid bearer token")
