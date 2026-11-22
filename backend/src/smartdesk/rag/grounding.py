from dataclasses import asdict

from smartdesk.observability.trace_events import record_event
from smartdesk.rag.rag_interfaces import AnswerModel
from smartdesk.rag.rag_models import AnswerResult, Citation, GroundedAnswer, Passage


class GroundingVerifier:
    def __init__(self, model: AnswerModel):
        self.model = model

    def verify(
        self, question: str, passages: list[Passage], answer: GroundedAnswer
    ) -> AnswerResult | None:
        valid = {p.id: p for p in passages}
        if not answer.answerable or not answer.claims:
            record_event("rag_abstention", stage="generation", reason="no_supported_claims")
            return None
        if any(
            not c.citation_ids or any(i not in valid for i in c.citation_ids) for c in answer.claims
        ):
            record_event("rag_abstention", stage="citation_validation", reason="invalid_citations")
            return None
        # Judge each atomic claim using only the sources attached to that claim.
        # Keep supported guidance if another, unnecessary claim fails verification.
        supported = []
        for claim in answer.claims:
            verdict = self.model.verify(
                {
                    "question": question,
                    "passages": [asdict(valid[i]) for i in dict.fromkeys(claim.citation_ids)],
                    "claim": claim.model_dump(),
                }
            )
            if verdict.supported:
                supported.append(claim)
        if not supported:
            record_event("rag_abstention", stage="verification", reason="unsupported_answer")
            return None
        # An omitted qualification can change the meaning of the surviving claims.
        if len(supported) != len(answer.claims):
            verdict = self.model.verify(
                {
                    "question": question,
                    "retained_claims": [claim.model_dump() for claim in supported],
                    "passages": [
                        asdict(valid[i])
                        for i in dict.fromkeys(i for c in supported for i in c.citation_ids)
                    ],
                }
            )
            if not verdict.supported:
                return None
        answer = answer.model_copy(update={"claims": supported})
        record_event("evidence_verified", claims=len(supported))
        used = list(dict.fromkeys(i for c in answer.claims for i in c.citation_ids))
        citations = [
            Citation(id=i, title=valid[i].title, excerpt=valid[i].text, source=valid[i].source)
            for i in used
        ]
        numbers = {i: n + 1 for n, i in enumerate(used)}
        text = "\n\n".join(
            c.text + " " + " ".join(f"[{numbers[i]}]" for i in dict.fromkeys(c.citation_ids))
            for c in answer.claims
        )
        return AnswerResult(text=text, citations=citations)
