from smartdesk.rag.answer_generation import AnswerGenerator
from smartdesk.rag.grounding import GroundingVerifier
from smartdesk.rag.interfaces import AnswerModel, Retriever
from smartdesk.rag.models import AnswerResult

ESCALATE = "I don't have enough information in the knowledge base to answer that reliably. Would you like me to prepare a support ticket?"


class QueryPipeline:
    """Public grounded-answer entry point, independent of HTTP and ticket workflows."""

    def __init__(self, retriever: Retriever, model: AnswerModel):
        self.retriever = retriever
        self.generator = AnswerGenerator(model)
        self.grounding = GroundingVerifier(model)

    def answer(self, question: str) -> AnswerResult:
        passages = self.retriever.search(question)
        if not passages:
            return AnswerResult(text=ESCALATE)
        answer = self.generator.generate(question, passages)
        return self.grounding.verify(question, passages, answer) or AnswerResult(text=ESCALATE)
