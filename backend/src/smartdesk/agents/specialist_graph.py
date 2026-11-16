"""Shared bounded agent execution: search, reason over evidence, verify."""

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from smartdesk.rag.query_pipeline import ESCALATE, QueryPipeline
from smartdesk.rag.rag_models import AnswerResult, GroundedAnswer, Passage
from smartdesk.tools.knowledge_search import KnowledgeSearchTool


class SpecialistState(TypedDict, total=False):
    route: dict
    passages: list[Passage]
    candidate: GroundedAnswer
    response: dict


def build_specialist_graph(pipeline: QueryPipeline, domain: str, prompt_file: str):
    instructions = (Path(__file__).parent / "prompts" / prompt_file).read_text(encoding="utf-8")
    search_tool = KnowledgeSearchTool(pipeline.retriever, domain)

    def search_knowledge(state: SpecialistState):
        return {"passages": search_tool.search(state["route"]["standalone_query"])}

    def generate_grounded_answer(state: SpecialistState):
        return {
            "candidate": pipeline.generator.generate(
                state["route"]["standalone_query"], state["passages"], instructions
            )
        }

    def verify_answer_evidence(state: SpecialistState):
        result = pipeline.grounding.verify(
            state["route"]["standalone_query"], state["passages"], state["candidate"]
        )
        return {"response": (result or AnswerResult(text=ESCALATE)).model_dump()}

    def offer_escalation(state: SpecialistState):
        return {"response": AnswerResult(text=ESCALATE).model_dump()}

    graph = StateGraph(SpecialistState)
    graph.add_node("search_domain_knowledge", search_knowledge)
    graph.add_node("generate_grounded_answer", generate_grounded_answer)
    graph.add_node("verify_answer_evidence", verify_answer_evidence)
    graph.add_node("offer_escalation", offer_escalation)
    graph.add_edge(START, "search_domain_knowledge")
    graph.add_conditional_edges(
        "search_domain_knowledge",
        lambda s: "generate_grounded_answer" if s["passages"] else "offer_escalation",
    )
    graph.add_edge("generate_grounded_answer", "verify_answer_evidence")
    graph.add_edge("verify_answer_evidence", END)
    graph.add_edge("offer_escalation", END)
    return graph.compile(name=f"{domain.lower()}_specialist")
