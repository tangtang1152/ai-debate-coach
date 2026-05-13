from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService
from app.utils.errors import AppError, ConflictError, LLMClientError
from app.utils.http import format_sse
from app.utils.prompt_builder import PromptBuilder


class DebateService:
    def __init__(
        self,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        llm_client,
        prompt_builder: PromptBuilder,
        max_rounds: int,
    ):
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.max_rounds = max_rounds
        self.session_service = SessionService(session_repository)

    def start_round_stream(self, session_id: str, content: str):
        session = self.session_service.get_session_or_raise(session_id)
        if session.current_round >= self.max_rounds:
            raise ConflictError("当前会话已完成 3 回合，不能继续发言。")

        round_no = session.current_round + 1
        history = self.message_repository.list_by_session(session_id)
        prompt_messages = self.prompt_builder.build_debate_messages(
            session=session,
            history=history,
            user_content=content,
        )

        def event_stream():
            collected_chunks: list[str] = []
            try:
                for chunk in self.llm_client.stream_debate_reply(
                    prompt_messages,
                    model=session.model_name,
                ):
                    if not chunk:
                        continue
                    collected_chunks.append(chunk)
                    yield format_sse(
                        "chunk",
                        {
                            "session_id": session_id,
                            "round_no": round_no,
                            "content": chunk,
                        },
                    )

                assistant_reply = "".join(collected_chunks).strip()
                if not assistant_reply:
                    raise LLMClientError("大模型没有返回有效反驳内容。")

                self.message_repository.add_message(
                    session_id=session_id,
                    role="user",
                    content=content,
                    round_no=round_no,
                )
                self.message_repository.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_reply,
                    round_no=round_no,
                )
                session.current_round = round_no
                self.session_repository.save(session)
                db.session.commit()

                yield format_sse(
                    "done",
                    {
                        "session_id": session_id,
                        "round_no": round_no,
                        "current_round": session.current_round,
                        "is_final_round": session.current_round >= self.max_rounds,
                    },
                )
            except Exception as exc:
                db.session.rollback()
                if isinstance(exc, AppError):
                    message = exc.message
                else:
                    current_app.logger.exception("Stream debate round failed: %s", exc)
                    message = "流式生成失败，请重试当前回合。"

                yield format_sse(
                    "error",
                    {
                        "session_id": session_id,
                        "round_no": round_no,
                        "message": message,
                    },
                )

        return event_stream()
