from smartdesk.agents.specialist_graph import build_specialist_graph
from smartdesk.rag.query_pipeline import QueryPipeline


def build_it_support_agent(pipeline: QueryPipeline):
    return build_specialist_graph(pipeline, "IT", "it_support.txt")
