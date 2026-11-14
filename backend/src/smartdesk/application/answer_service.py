from dataclasses import asdict

from smartdesk.api.schemas import ChatResponse, Citation
from smartdesk.application.ports import Retriever
from smartdesk.infrastructure.llm.client import LanguageModel

ESCALATE = "I don't have enough information in the knowledge base to answer that reliably. Would you like me to prepare a support ticket?"


class AnswerService:
    def __init__(self, retriever: Retriever, model: LanguageModel):
        self.retriever = retriever
        self.model = model

    def answer(self, question: str) -> ChatResponse:
        passages = self.retriever.search(question)
        if not passages:
            return ChatResponse(text=ESCALATE)
        data = {"question": question, "passages": [asdict(p) for p in passages]}
        answer = self.model.answer(data)
        valid = {p.id: p for p in passages}
        if not answer.answerable or not answer.claims:
            return ChatResponse(text=ESCALATE)
        if any(
            not c.citation_ids or any(i not in valid for i in c.citation_ids) for c in answer.claims
        ):
            return ChatResponse(text=ESCALATE)
        verdict = self.model.verify({**data, "answer": answer.model_dump()})
        if not verdict.supported:
            return ChatResponse(text=ESCALATE)
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
        return ChatResponse(text=text, citations=citations)
