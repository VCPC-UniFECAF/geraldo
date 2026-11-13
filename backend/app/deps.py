import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db import get_session
from app.models import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def user_from_token(token: str, session: Session) -> User | None:
    """O usuário dono do token, ou None se o token for inválido, expirado ou de usuário que não existe."""
    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        return None
    return session.get(User, int(claims["sub"]))


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    user = user_from_token(creds.credentials, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre de novo.")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Seu perfil não tem permissão para isso.")
        return user

    return checker
