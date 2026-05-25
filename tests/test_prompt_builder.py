from __future__ import annotations

from types import SimpleNamespace

from app.utils.prompt_builder import PromptBuilder


def test_prompt_builder():
    builder = PromptBuilder(history_limit=4, max_rounds=3)
    session = SimpleNamespace(topic="安乐死是否应该合法化", position="正方", current_round=1)
    history = [
        SimpleNamespace(role="user", content="我方认为应尊重患者自主。", round_no=1),
        SimpleNamespace(role="assistant", content="自主并不意味着社会可放弃保护生命。", round_no=1),
    ]

    messages = builder.build_debate_messages(
        session=session,
        history=history,
        user_content="制度设计可以配合严格审核。",
    )

    assert messages[0]["role"] == "system"
    assert "安乐死是否应该合法化" in messages[0]["content"]
    assert "反方" in messages[0]["content"]
    assert "连续攻防" in messages[0]["content"]
    assert messages[-1]["content"] == "制度设计可以配合严格审核。"
    assert len(messages) == 4


def test_evaluation_prompt_requires_complete_debate_context():
    builder = PromptBuilder(history_limit=6, max_rounds=3)
    session = SimpleNamespace(topic="人工智能是否利大于弊", position="正方", current_round=3)
    history = [
        SimpleNamespace(role="user", content="AI 可以提升生产效率。", round_no=1),
        SimpleNamespace(role="assistant", content="效率提升可能伴随岗位替代。", round_no=1),
        SimpleNamespace(role="user", content="岗位变化可以通过再培训解决。", round_no=2),
    ]

    messages = builder.build_evaluation_messages(session=session, history=history)

    assert "完整三轮攻防记录" in messages[0]["content"]
    assert "不能只看最后一轮" in messages[0]["content"]
    assert "是否回应了 AI 上一轮的挑战" in messages[1]["content"]
    assert "AI 可以提升生产效率。" in messages[1]["content"]
