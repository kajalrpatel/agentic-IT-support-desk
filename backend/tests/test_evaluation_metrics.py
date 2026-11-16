import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluations/runners"))
from types import SimpleNamespace

from answer_evaluators import AnswerJudgment, build_answer_judge, citation_coverage
from langsmith_experiment import score_retrieval
from report_metrics import retrieval_scores


def test_recall_deduplicates_and_mrr_uses_first_relevant_rank():
    assert retrieval_scores(["wrong", "a", "a", "b", "c", "d"], ["a", "d"]) == {
        "recall_at_5": 0.5,
        "mrr": 0.5,
    }


def test_langsmith_feedback_uses_expected_document_labels():
    result = score_retrieval(
        SimpleNamespace(outputs={"retrieved": ["wrong", "correct"]}),
        SimpleNamespace(outputs={"expected_documents": ["correct"]}),
    )
    assert result["results"] == [{"key": "recall_at_5", "score": 1.0}, {"key": "mrr", "score": 0.5}]


def test_uncited_answer_does_not_get_fabricated_judge_score():
    run = SimpleNamespace(outputs={"response": {"citations": []}, "retrieved_contexts": []})
    assert build_answer_judge(None)(run, None) == {"results": []}
    assert citation_coverage(run, None)["score"] == 0


def test_answer_judge_returns_validated_scores():
    from unittest.mock import Mock

    client = Mock()
    client.responses.parse.return_value.output_parsed = AnswerJudgment(
        faithfulness=0.5, relevance=1, explanation="Partially supported"
    )
    run = SimpleNamespace(
        outputs={
            "response": {"text": "Example", "citations": [{"id": "a"}]},
            "retrieved_contexts": ["Evidence"],
        }
    )
    result = build_answer_judge(client)(run, SimpleNamespace(inputs={"query": "Question"}))
    assert [score["score"] for score in result["results"]] == [0.5, 1]
    assert client.responses.parse.call_args.kwargs["model"] == "gpt-4o-mini"
