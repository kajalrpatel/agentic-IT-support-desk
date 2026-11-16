from dataclasses import asdict

from smartdesk.rag.rag_interfaces import AnswerModel
from smartdesk.rag.rag_models import GroundedAnswer, Passage


class AnswerGenerator:
    def __init__(self, model: AnswerModel):
        self.model = model

    def generate(
        self, question: str, passages: list[Passage], instructions: str = ""
    ) -> GroundedAnswer:
        return self.model.answer(
            {
                "question": question,
                "passages": [asdict(p) for p in passages],
                "specialist_instructions": instructions,
            }
        )
