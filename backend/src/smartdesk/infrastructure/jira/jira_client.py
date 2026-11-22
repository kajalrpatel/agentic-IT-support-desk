import re
import time

import httpx

from smartdesk.config import Settings
from smartdesk.domain.support_models import ServiceError, Ticket, TicketWriteRejected


def plain_text(value) -> str:
    if isinstance(value, dict):
        own = value.get("text", "")
        return own + " ".join(plain_text(v) for v in value.get("content", []))
    return value if isinstance(value, str) else ""


class JiraClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.base = settings.jira_base_url.rstrip("/")
        self.client = client or httpx.Client(
            auth=(settings.jira_email, settings.jira_api_token.get_secret_value()),
            timeout=settings.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )

    def request(self, method: str, path: str, **kwargs):
        if not self.base or not self.settings.jira_project_key:
            raise TicketWriteRejected(
                "Jira is not configured. Your draft is saved; contact the administrator."
            )
        for attempt in range(3 if method == "GET" else 1):
            try:
                response = self.client.request(method, self.base + "/rest/api/3" + path, **kwargs)
                if response.status_code in (429, 502, 503, 504) and method == "GET" and attempt < 2:
                    time.sleep(0.3 * 2**attempt)
                    continue
                if response.status_code >= 400:
                    if method == "POST" and response.status_code in {400, 401, 403, 404, 422, 429}:
                        raise TicketWriteRejected(
                            "Jira rejected the submission. Check its required fields, permissions, and rate limits before retrying."
                        )
                    raise ServiceError(
                        "Jira could not complete the request. Check project permissions and configuration, then retry."
                    )
                return response.json()
            except httpx.HTTPError as exc:
                if method == "GET" and attempt < 2:
                    time.sleep(0.3 * 2**attempt)
                    continue
                raise ServiceError(
                    "Jira is temporarily unreachable. Your request has been preserved."
                ) from exc
        raise ServiceError("Jira is temporarily unavailable.")

    def create(self, draft: dict, correlation: str, employee_label: str) -> Ticket:
        body = f"Employee: {draft['email']}\nCategory: {draft['category']}\nRequested priority: {draft['priority']}\n\n{draft['description']}"
        result = self.request(
            "POST",
            "/issue",
            json={
                "fields": {
                    "project": {"key": self.settings.jira_project_key},
                    "issuetype": {"name": self.settings.jira_issue_type},
                    "summary": draft["summary"],
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": body}]}
                        ],
                    },
                    "labels": [correlation, employee_label, "smartdesk", draft["category"].lower()],
                }
            },
        )
        key = result["key"]
        return Ticket(key, draft["summary"], "Created", f"{self.base}/browse/{key}")

    def convert(self, issue: dict) -> Ticket:
        fields = issue["fields"]
        return Ticket(
            issue["key"],
            fields["summary"],
            fields["status"]["name"],
            f"{self.base}/browse/{issue['key']}",
        )

    def find(self, label: str) -> list[Ticket]:
        if not re.fullmatch(r"[a-z0-9-]+", label) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]*", self.settings.jira_project_key
        ):
            raise ServiceError("Invalid ticket lookup configuration.")
        return self._search(f'labels = "{label}"')

    def find_owned(self, email: str, label: str) -> list[Ticket]:
        labelled = self.find(label)
        if email.casefold() == self.settings.jira_email.casefold():
            return labelled
        users = self.request("GET", "/user/search", params={"query": email, "maxResults": 100})
        ids = {
            u["accountId"]
            for u in users
            if (u.get("emailAddress") or "").casefold() == email.casefold() and u.get("accountId")
        }
        if len(ids) != 1:
            return labelled
        account = ids.pop()
        if not re.fullmatch(r"[A-Za-z0-9:_-]+", account):
            raise ServiceError("Unable to verify your Jira account.")
        reported = self._search(f'reporter = "{account}"', exclude_managed=True)
        return list({t.id: t for t in [*labelled, *reported]}.values())

    def _search(self, condition: str, *, exclude_managed: bool = False) -> list[Ticket]:
        tickets: list[Ticket] = []
        token = None
        for _ in range(50):
            params = {
                "jql": f'project = "{self.settings.jira_project_key}" AND {condition} ORDER BY created DESC',
                "fields": "summary,status,labels",
                "maxResults": 100,
            }
            if token:
                params["nextPageToken"] = token
            result = self.request("GET", "/search/jql", params=params)
            for issue in result.get("issues", []):
                labels = issue["fields"].get("labels")
                if exclude_managed and (
                    labels is None
                    or any(tag == "smartdesk" or tag.startswith("sd-employee-") for tag in labels)
                ):
                    continue
                tickets.append(self.convert(issue))
            token = result.get("nextPageToken")
            if not token:
                return tickets
        raise ServiceError("Too many matching tickets. Narrow the request with a ticket ID.")

    def get(self, ticket_id: str) -> Ticket:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", ticket_id):
            raise ServiceError("Invalid ticket ID.", 422)
        ticket = self.convert(
            self.request("GET", f"/issue/{ticket_id}", params={"fields": "summary,status"})
        )
        start = 0
        for _ in range(50):
            page = self.request(
                "GET", f"/issue/{ticket_id}/comment", params={"startAt": start, "maxResults": 100}
            )
            comments = page.get("comments", [])
            # A service account can see internal notes. Never expose restricted comments.
            ticket.comments.extend(
                plain_text(c.get("body", ""))
                for c in comments
                if not c.get("visibility") and c.get("jsdPublic") is not False
            )
            start += len(comments)
            if not comments or start >= page.get("total", 0):
                break
        return ticket
