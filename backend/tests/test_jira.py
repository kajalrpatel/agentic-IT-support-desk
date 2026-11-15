import httpx
import pytest

from smartdesk.config import Settings
from smartdesk.domain.support_models import ServiceError
from smartdesk.infrastructure.jira.jira_client import JiraClient


def jira(handler):
    settings = Settings(
        session_secret="test-secret-that-is-more-than-32-characters",
        jira_base_url="https://jira.example.com",
        jira_project_key="IT",
    )
    return JiraClient(settings, httpx.Client(transport=httpx.MockTransport(handler)))


def test_jira_paginates_search_and_filters_comments():
    def handler(request):
        if "search/jql" in request.url.path:
            if "nextPageToken" not in request.url.params:
                return httpx.Response(
                    200,
                    json={
                        "issues": [
                            {
                                "key": "IT-1",
                                "fields": {"summary": "VPN", "status": {"name": "Open"}},
                            }
                        ],
                        "nextPageToken": "next",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "issues": [
                        {
                            "key": "IT-2",
                            "fields": {"summary": "Mail", "status": {"name": "Resolved"}},
                        }
                    ]
                },
            )
        if request.url.path.endswith("/comment"):
            return httpx.Response(
                200,
                json={
                    "total": 2,
                    "comments": [
                        {"body": "Public update"},
                        {"body": "Internal note", "visibility": {"type": "role"}},
                    ],
                },
            )
        return httpx.Response(
            200,
            json={"key": "IT-1", "fields": {"summary": "VPN", "status": {"name": "In Progress"}}},
        )

    client = jira(handler)
    assert len(client.find("sd-employee-test")) == 2
    ticket = client.get("IT-1")
    assert ticket.status == "In Progress" and ticket.comments == ["Public update"]


def test_create_timeout_is_never_retried():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("response lost")

    client = jira(handler)
    with pytest.raises(ServiceError):
        client.create(
            {
                "email": "jane@example.com",
                "category": "IT",
                "priority": "Medium",
                "description": "Issue",
                "summary": "Issue",
            },
            "sd-request-one",
            "sd-employee-one",
        )
    assert len(calls) == 1
