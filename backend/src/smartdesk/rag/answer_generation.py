from dataclasses import asdict

from smartdesk.rag.interfaces import AnswerModel
from smartdesk.rag.models import GroundedAnswer, Passage


class AnswerGenerator:
    def __init__(self, model: AnswerModel):
        self.model = model

    def generate(self, question: str, passages: list[Passage]) -> GroundedAnswer:
        return self.model.answer({"question": question, "passages": [asdict(p) for p in passages]})
