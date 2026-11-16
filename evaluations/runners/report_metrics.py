"""Deterministic retrieval metrics, independent of hosted services."""


def answer_behavior_scores(answers):
    labelled = [a for a in answers if a.get("expected_domain")]
    known = [a for a in answers if a["expected_answerable"]]
    unknown = [a for a in answers if not a["expected_answerable"]]
    return {
        "domain_routing_accuracy": sum(
            a["route"]["intent"] == "knowledge" and a["route"]["category"] == a["expected_domain"]
            for a in labelled
        )
        / len(labelled)
        if labelled
        else None,
        "answerable_citation_coverage": sum(bool(a["response"]["citations"]) for a in known)
        / len(known)
        if known
        else None,
        "unknown_no_citation_rate": sum(not a["response"]["citations"] for a in unknown)
        / len(unknown)
        if unknown
        else None,
        "known_count": len(known),
        "unknown_count": len(unknown),
        "note": "Citation coverage and absence are proxies, not correctness or escalation accuracy.",
    }


def retrieval_scores(retrieved, expected):
    expected = set(expected)
    if not expected:
        raise ValueError("Expected document labels are required")
    top = retrieved[:5]
    rank = next((i for i, value in enumerate(top, 1) if value in expected), None)
    return {
        "recall_at_5": len(set(top) & expected) / len(expected),
        "mrr": 1 / rank if rank else 0.0,
    }


def compare_retrieval_modes(modes):
    baseline = modes["dense"]
    return {
        name: {
            f"{metric}_delta_vs_dense": value[metric] - baseline[metric]
            for metric in ("recall_at_5", "mrr", "mean_latency_ms")
        }
        for name, value in modes.items()
        if name != "dense"
    }
