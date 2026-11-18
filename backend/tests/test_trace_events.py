from unittest.mock import Mock

from smartdesk.observability import trace_events


def test_event_attaches_safe_attributes_to_active_span(monkeypatch):
    run = Mock()
    monkeypatch.setattr(trace_events, "get_current_run_tree", lambda: run)
    trace_events.record_event("retrieval_completed", domain="IT", passage_count=5)
    event = run.add_event.call_args.args[0]
    assert event["name"] == "retrieval_completed"
    assert event["kwargs"] == {"domain": "IT", "passage_count": 5}


def test_event_is_safe_without_tracing(monkeypatch):
    monkeypatch.setattr(trace_events, "get_current_run_tree", lambda: None)
    trace_events.record_event("rag_abstention", stage="generation")
