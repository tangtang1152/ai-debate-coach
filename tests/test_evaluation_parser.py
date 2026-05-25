from __future__ import annotations

import pytest

from app.utils.evaluation_parser import EvaluationParser


class TestEvaluationParser:
    @pytest.fixture
    def parser(self):
        return EvaluationParser()

    def test_parse_valid_json(self, parser):
        result = parser.parse(
            '{"logic_score": 8, "evidence_score": 7, '
            '"fluency_score": 6, "suggestion": "需要补强数据。"}'
        )

        assert result.logic_score == 8
        assert result.evidence_score == 7
        assert result.fluency_score == 6
        assert result.suggestion == "需要补强数据。"
        assert result.fallback_used is False

    def test_parse_json_in_markdown_fence_with_language(self, parser):
        result = parser.parse(
            '```json\n{"logic_score": 5, "evidence_score": 4, '
            '"fluency_score": 7, "suggestion": "请补充例证。"}\n```'
        )

        assert result.logic_score == 5
        assert result.evidence_score == 4
        assert result.fluency_score == 7
        assert result.suggestion == "请补充例证。"
        assert result.fallback_used is False

    def test_parse_json_in_markdown_fence_without_language(self, parser):
        result = parser.parse(
            '```\n{"logic_score": 9, "evidence_score": 8, '
            '"fluency_score": 7, "suggestion": "论证完整。"}\n```'
        )

        assert result.logic_score == 9
        assert result.fallback_used is False

    def test_parse_json_embedded_in_text(self, parser):
        result = parser.parse(
            '这是评分结果：{"logic_score": 6, "evidence_score": 5, '
            '"fluency_score": 8, "suggestion": "尝试使用更多数据。"}感谢使用。'
        )

        assert result.logic_score == 6
        assert result.evidence_score == 5
        assert result.fluency_score == 8
        assert result.fallback_used is False

    def test_parse_score_aliases(self, parser):
        result = parser.parse(
            '{"logic": 7, "evidence": 6, "fluency": 5, '
            '"suggestion": "继续加油。"}'
        )

        assert result.logic_score == 7
        assert result.evidence_score == 6
        assert result.fluency_score == 5
        assert result.fallback_used is False

    def test_parse_clamps_scores_to_range(self, parser):
        result = parser.parse(
            '{"logic_score": 15, "evidence_score": -3, '
            '"fluency_score": 0, "suggestion": "极端分数测试。"}'
        )

        assert result.logic_score == 10
        assert result.evidence_score == 0
        assert result.fluency_score == 0

    def test_parse_missing_score_fields_use_default(self, parser):
        result = parser.parse(
            '{"logic_score": 7, "suggestion": "缺少两个分数维度。"}'
        )

        assert result.logic_score == 7
        assert result.evidence_score == EvaluationParser.DEFAULT_SCORE
        assert result.fluency_score == EvaluationParser.DEFAULT_SCORE

    def test_parse_null_scores_use_default(self, parser):
        result = parser.parse(
            '{"logic_score": null, "evidence_score": null, '
            '"fluency_score": null, "suggestion": "全部为空。"}'
        )

        assert result.logic_score == EvaluationParser.DEFAULT_SCORE
        assert result.evidence_score == EvaluationParser.DEFAULT_SCORE
        assert result.fluency_score == EvaluationParser.DEFAULT_SCORE

    def test_parse_missing_suggestion_uses_default(self, parser):
        result = parser.parse(
            '{"logic_score": 8, "evidence_score": 7, "fluency_score": 6}'
        )

        assert result.suggestion == EvaluationParser.DEFAULT_SUGGESTION

    def test_parse_empty_suggestion_uses_default(self, parser):
        result = parser.parse(
            '{"logic_score": 8, "evidence_score": 7, "fluency_score": 6, '
            '"suggestion": ""}'
        )

        assert result.suggestion == EvaluationParser.DEFAULT_SUGGESTION

    def test_parse_whitespace_only_suggestion_uses_default(self, parser):
        result = parser.parse(
            '{"logic_score": 8, "evidence_score": 7, "fluency_score": 6, '
            '"suggestion": "   "}'
        )

        assert result.suggestion == EvaluationParser.DEFAULT_SUGGESTION

    def test_parse_completely_invalid_text_triggers_fallback(self, parser):
        result = parser.parse("这不是 JSON，只是纯文本回复。")

        assert result.logic_score == EvaluationParser.DEFAULT_SCORE
        assert result.evidence_score == EvaluationParser.DEFAULT_SCORE
        assert result.fluency_score == EvaluationParser.DEFAULT_SCORE
        assert result.suggestion == EvaluationParser.DEFAULT_SUGGESTION
        assert result.fallback_used is True

    def test_parse_empty_string_triggers_fallback(self, parser):
        result = parser.parse("")

        assert result.fallback_used is True

    def test_parse_string_scores_are_coerced(self, parser):
        result = parser.parse(
            '{"logic_score": "8", "evidence_score": "7", '
            '"fluency_score": "6", "suggestion": "字符串数字测试。"}'
        )

        assert result.logic_score == 8
        assert result.evidence_score == 7
        assert result.fluency_score == 6
        assert result.fallback_used is False

    def test_parse_suggestion_is_stripped(self, parser):
        result = parser.parse(
            '{"logic_score": 7, "evidence_score": 6, "fluency_score": 8, '
            '"suggestion": "  请补充数据支撑。  "}'
        )

        assert result.suggestion == "请补充数据支撑。"
