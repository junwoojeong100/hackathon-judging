"""Optional admin-token gate for mutating endpoints.

When ADMIN_TOKEN is unset the app stays fully open (demo mode). When it is set,
submit / upload / rejudge / delete / rubric-edit require a matching X-Admin-Token
header.
"""
from fastapi import Header, HTTPException

from .config import settings


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        return  # open mode — no token configured
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=401, detail="이 작업에는 관리자 토큰(X-Admin-Token)이 필요합니다."
        )
