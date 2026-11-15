"""Explicit, repeat-safe smoke test for the user's dedicated Jira test project."""

import argparse
import json
from pathlib import Path

from smartdesk.application.ticket_service import employee_label
from smartdesk.config import Settings
from smartdesk.domain.support_models import ServiceError
from smartdesk.infrastructure.jira.jira_client import JiraClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-ticket", action="store_true")
    args = parser.parse_args()
    settings = Settings(_env_file="../.env")
    client = JiraClient(settings)
    marker = Path(".cache/jira-smoke-attempt.json")
    correlation = "sd-smoke-verification-20261108"
    try:
        client.request("GET", f"/project/{settings.jira_project_key}")
        matches = client.find(correlation)
        if matches:
            ticket = matches[0]
        elif marker.exists():
            print("Previous write outcome requires reconciliation. No new ticket created.")
            return
        elif args.create_ticket:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"correlation": correlation, "status": "attempted"}))
            ticket = client.create(
                {
                    "email": settings.demo_email,
                    "summary": "[SmartDesk smoke test] API integration verification",
                    "description": "Authorized integration smoke test with fictional employee data. No support action is required. This verifies issue creation and live status retrieval.",
                    "category": "IT",
                    "priority": "Low",
                },
                correlation,
                employee_label(settings.demo_email),
            )
            marker.write_text(json.dumps({"correlation": correlation, "ticket_id": ticket.id}))
        else:
            print(
                "Project access and search passed. Use --create-ticket only for an authorized test project."
            )
            return
        actual = client.get(ticket.id)
        print(
            json.dumps(
                {
                    "ticket_id": actual.id,
                    "status": actual.status,
                    "url": actual.url,
                    "create_read": "passed",
                }
            )
        )
    except ServiceError as exc:
        print(json.dumps({"result": "failed", "detail": str(exc)}))
        raise SystemExit(1) from None
    finally:
        client.client.close()


if __name__ == "__main__":
    main()
