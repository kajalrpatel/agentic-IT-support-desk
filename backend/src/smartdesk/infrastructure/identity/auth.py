from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.concurrency import run_in_threadpool

from smartdesk.config import Settings
from smartdesk.domain.models import Identity


class Auth:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks = (
            jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True)
            if settings.auth_mode == "oidc"
            else None
        )

    def demo_token(self):
        if self.settings.auth_mode != "demo" or self.settings.environment == "production":
            raise HTTPException(404)
        return jwt.encode(
            {
                "sub": "demo-jane",
                "email": self.settings.demo_email,
                "email_verified": True,
                "iss": "smartdesk-demo",
                "aud": "smartdesk",
                "exp": datetime.now(UTC) + timedelta(hours=8),
            },
            self.settings.session_secret.get_secret_value(),
            algorithm="HS256",
        )

    def identity(self, token: str) -> Identity:
        try:
            if self.jwks:
                key = self.jwks.get_signing_key_from_jwt(token).key
                claims = jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    audience=self.settings.oidc_audience,
                    issuer=self.settings.oidc_issuer,
                    options={"require": ["exp", "sub", "email", "email_verified"]},
                )
            else:
                claims = jwt.decode(
                    token,
                    self.settings.session_secret.get_secret_value(),
                    algorithms=["HS256"],
                    audience="smartdesk",
                    issuer="smartdesk-demo",
                    options={"require": ["exp", "sub", "email"]},
                )
            if claims.get("email_verified") is not True:
                raise HTTPException(403, "A verified employee email is required.")
            return Identity(claims["sub"], claims["email"])
        except (jwt.PyJWTError, KeyError) as exc:
            raise HTTPException(401, "Please sign in again.") from exc


bearer = HTTPBearer()


async def current_identity(request: Request) -> Identity:
    credentials = await bearer(request)
    if credentials is None:
        raise HTTPException(401, "Please sign in.")
    return await run_in_threadpool(
        request.app.state.services.auth.identity, credentials.credentials
    )
