from fastapi import APIRouter, Depends, Request

from smartdesk.domain.support_models import Identity
from smartdesk.infrastructure.identity.authentication import current_identity

router = APIRouter()


@router.get("/api/v1/auth/config")
def auth_config(request: Request):
    return {"mode": request.app.state.settings.auth_mode}


@router.post("/api/v1/auth/demo")
def demo(request: Request):
    return {
        "token": request.app.state.services.auth.demo_token(),
        "email": request.app.state.settings.demo_email,
    }


@router.get("/api/v1/me")
def me(identity: Identity = Depends(current_identity)):
    return {"email": identity.email}
