from __future__ import annotations

from flask import Blueprint, Response, current_app, request, stream_with_context

from app.clients.llm_client import LLMClient
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.debate import (
    parse_evaluate_payload,
    parse_start_payload,
    parse_stream_payload,
)
from app.services.debate_service import DebateService
from app.services.evaluation_service import EvaluationService
from app.services.session_service import SessionService
from app.utils.evaluation_parser import EvaluationParser
from app.utils.http import success_response
from app.utils.prompt_builder import PromptBuilder

debate_bp = Blueprint("debate", __name__)


def _build_session_service() -> SessionService:
    return SessionService(SessionRepository())


def _build_debate_service() -> DebateService:
    prompt_builder = PromptBuilder(
        history_limit=current_app.config["PROMPT_HISTORY_LIMIT"],
        max_rounds=current_app.config["MAX_DEBATE_ROUNDS"],
    )
    return DebateService(
        session_repository=SessionRepository(),
        message_repository=MessageRepository(),
        llm_client=LLMClient(current_app.config),
        prompt_builder=prompt_builder,
        max_rounds=current_app.config["MAX_DEBATE_ROUNDS"],
    )


def _build_evaluation_service() -> EvaluationService:
    prompt_builder = PromptBuilder(
        history_limit=current_app.config["PROMPT_HISTORY_LIMIT"],
        max_rounds=current_app.config["MAX_DEBATE_ROUNDS"],
    )
    return EvaluationService(
        session_repository=SessionRepository(),
        message_repository=MessageRepository(),
        evaluation_repository=EvaluationRepository(),
        llm_client=LLMClient(current_app.config),
        prompt_builder=prompt_builder,
        evaluation_parser=EvaluationParser(),
        max_rounds=current_app.config["MAX_DEBATE_ROUNDS"],
    )


@debate_bp.post("/start")
def start_debate():
    payload = parse_start_payload(request.get_json(silent=True))
    session = _build_session_service().create_session(
        topic=payload.topic,
        position=payload.position,
        model_name=payload.model,
    )
    return success_response(
        {
            "session_id": session.id,
            "topic": session.topic,
            "position": session.position,
            "model": session.model_name,
            "current_round": session.current_round,
            "status": session.status,
        },
        status_code=201,
    )


@debate_bp.post("/stream")
def stream_debate():
    payload = parse_stream_payload(request.get_json(silent=True))
    stream = _build_debate_service().start_round_stream(
        session_id=payload.session_id,
        content=payload.content,
    )
    return Response(
        stream_with_context(stream),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@debate_bp.post("/evaluate")
def evaluate_debate():
    payload = parse_evaluate_payload(request.get_json(silent=True))
    evaluation, fallback_used, cached = _build_evaluation_service().evaluate_session(
        payload.session_id
    )
    return success_response(
        {
            "session_id": evaluation.session_id,
            "logic_score": evaluation.logic_score,
            "evidence_score": evaluation.evidence_score,
            "fluency_score": evaluation.fluency_score,
            "suggestion": evaluation.suggestion,
            "fallback_used": fallback_used,
            "cached": cached,
        }
    )
