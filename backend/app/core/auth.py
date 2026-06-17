"""
app/core/auth.py
────────────────
JWT authentication (HS256).
For production, swap to RS256 with Azure AD OIDC (see comments).
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class TokenData(BaseModel):
    username: Optional[str] = None


class UserContext(BaseModel):
    username: str
    email: Optional[str] = None
    roles: list[str] = []


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return UserContext(
            username=username,
            email=payload.get("email"),
            roles=payload.get("roles", []),
        )
    except JWTError:
        raise credentials_exception


# ── Demo token endpoint (replace with Azure AD OIDC in prod) ────
from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Demo endpoint. In production this is replaced by Azure AD OIDC redirect.
    Accepts any username/password for local dev.
    """
    # TODO: validate against Azure AD / internal user store
    token = create_access_token({"sub": form_data.username, "roles": ["analyst"]})
    return {"access_token": token, "token_type": "bearer"}
