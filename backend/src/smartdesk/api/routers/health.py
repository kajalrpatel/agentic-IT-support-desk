from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request):
    configuration = request.app.state.settings
    try:
        request.app.state.services.repo.check_readiness()
        return {
            "status": "ready",
            "llm_configured": bool(configuration.openai_api_key.get_secret_value()),
            "jira_configured": bool(
                configuration.jira_base_url and configuration.jira_api_token.get_secret_value()
            ),
        }
    except Exception:
        return JSONResponse({"status": "not_ready"}, status_code=503)
