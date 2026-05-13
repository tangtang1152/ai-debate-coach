from __future__ import annotations

from app.extensions import db
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService
from app.utils.errors import ConflictError
from app.utils.evaluation_parser import EvaluationParser
from app.utils.prompt_builder import PromptBuilder


class EvaluationService:
    def __init__(
        self,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        evaluation_repository: EvaluationRepository,
        llm_client,
        prompt_builder: PromptBuilder,
        evaluation_parser: EvaluationParser,
        max_rounds: int,
    ):
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.evaluation_repository = evaluation_repository
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.evaluation_parser = evaluation_parser
        self.max_rounds = max_rounds
        self.session_service = SessionService(session_repository)

    def evaluate_session(self, session_id: str):
        session = self.session_service.get_session_or_raise(session_id)
        if session.current_round < self.max_rounds:
            raise ConflictError(
                "当前会话尚未完成 3 回合，暂不能生成评分。",
                details={"current_round": session.current_round},
            )

        existing = self.evaluation_repository.get_by_session_id(session_id)
        if existing is not None:
            return existing, False, True

        history = self.message_repository.list_by_session(session_id)
        if not history:
            raise ConflictError("当前会话没有可用于评分的消息历史。")

        prompt_messages = self.prompt_builder.build_evaluation_messages(session, history)
        raw_text = self.llm_client.generate_evaluation(
            prompt_messages,
            model=session.model_name,
        )
        parsed = self.evaluation_parser.parse(raw_text)

        evaluation = self.evaluation_repository.create(
            session_id=session_id,
            logic_score=parsed.logic_score,
            evidence_score=parsed.evidence_score,
            fluency_score=parsed.fluency_score,
            suggestion=parsed.suggestion,
        )
        db.session.commit()
        return evaluation, parsed.fallback_used, False
