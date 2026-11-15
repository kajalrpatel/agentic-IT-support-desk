from dataclasses import asdict

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
            return None
        if any(
            not c.citation_ids or any(i not in valid for i in c.citation_ids) for c in answer.claims
        ):
            return None
        verdict = self.model.verify(
            {
                "question": question,
                "passages": [asdict(p) for p in passages],
                "answer": answer.model_dump(),
            }
        )
        if not verdict.supported:
            return None
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
