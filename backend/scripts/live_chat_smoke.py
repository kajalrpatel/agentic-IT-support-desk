"""Small paid-model smoke test through the running app; never confirms a ticket."""

import json
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

BASE = "http://127.0.0.1:8080/api/v1"


def main():
    token = ""

    def call(path, data=None):
        request = urllib.request.Request(
            BASE + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)

    token = call("/auth/demo", {})["token"]
    conversation = call("/conversations", {})["id"]
    results = []
    cases = [
        ("it_answer", "How do I reset a forgotten password?", True),
        ("follow_up", "What if it still does not work?", True),
        ("hr_answer", "How long do I have to use compensatory time off?", True),
        ("unknown", "What is the exact annual dental insurance reimbursement limit?", False),
        (
            "draft",
            "Create an IT ticket: my VPN disconnects every five minutes. I restarted the computer and checked my internet connection, but the issue persists. Priority low.",
            False,
        ),
    ]
    for name, query, needs_citations in cases:
        started = time.monotonic()
        response = call(
            f"/conversations/{conversation}/messages",
            {"request_id": str(uuid4()), "text": query},
        )
        passed = bool(response["citations"]) if needs_citations else not response["citations"]
        if name == "unknown":
            passed = passed and "ticket" in response["text"].lower()
        if name == "draft":
            passed = bool(response["pending_approval"] and response["draft"])
        results.append(
            {
                "case": name,
                "query": query,
                "passed": passed,
                "seconds": round(time.monotonic() - started, 2),
                "response": response,
            }
        )
        print(json.dumps(results[-1]), flush=True)
        if name == "draft" and response["pending_approval"]:
            cancelled = call(
                f"/conversations/{conversation}/approval",
                {
                    "request_id": str(uuid4()),
                    "version": response["draft_version"],
                    "action": "cancel",
                },
            )
            results.append(
                {
                    "case": "cancel",
                    "passed": not cancelled["pending_approval"] and not cancelled["tickets"],
                    "response": cancelled,
                }
            )
    restored = call(f"/conversations/{conversation}")
    report = {
        "conversation_id": conversation,
        "cases": results,
        "restored_messages": len(restored["messages"]),
        "all_checks_passed": all(r["passed"] for r in results),
    }
    target = Path("../evaluations/reports/live_smoke.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "all_checks_passed": report["all_checks_passed"],
                "restored_messages": report["restored_messages"],
            }
        )
    )
    if not report["all_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
