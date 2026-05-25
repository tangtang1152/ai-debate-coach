from __future__ import annotations

from app.schemas.evaluation import EvaluationResult


class TestEvaluationResult:
    def test_to_dict(self):
        result = EvaluationResult(
            logic_score=8,
            evidence_score=7,
            fluency_score=6,
            suggestion="需要改进。",
        )
        d = result.to_dict()
        assert d == {
            "logic_score": 8,
            "evidence_score": 7,
            "fluency_score": 6,
            "suggestion": "需要改进。",
            "fallback_used": False,
        }

    def test_to_dict_with_fallback(self):
        result = EvaluationResult(
            logic_score=5,
            evidence_score=5,
            fluency_score=5,
            suggestion="",
            fallback_used=True,
        )
        d = result.to_dict()
        assert d["fallback_used"] is True

    def test_default_fallback_used_is_false(self):
        result = EvaluationResult(
            logic_score=5, evidence_score=5, fluency_score=5, suggestion="test"
        )
        assert result.fallback_used is False
