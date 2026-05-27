"""Main chat orchestration service with SSE streaming."""

import json
import uuid
import time
import httpx
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging.logger import get_logger
from app.core.qstash.producer import qstash_producer
from app.core.qstash.topics import QStashTopics
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService
from app.services.followup_service import FollowupService
from app.memory.orchestrator import MemoryOrchestrator
from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.llm.llm_service import llm_service

logger = get_logger(__name__)


class ChatService:
    def __init__(self):
        self.message_repo = MessageRepository()
        self.session_repo = SessionRepository()
        self.session_service = SessionService()
        self.followup_service = FollowupService()
        self.memory_orchestrator = MemoryOrchestrator()
        self.rag_pipeline = RAGPipeline()

    async def process_chat_stream(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Main chat processing with SSE streaming."""
        start_time = time.time()

        # 1. Save user message to DB
        await self.message_repo.create_message(
            db=db,
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=message,
            metadata_json=None,
            token_count=None,
        )

        # 2. Auto-generate title if first message
        msg_count = await self.message_repo.count_session_messages(db, session_id)
        if msg_count == 1:
            await self.session_service.auto_generate_title(db, session_id, message)

        # 3. Get memory context (STM + LTM)
        try:
            memory_context = await self.memory_orchestrator.get_context(
                user_id=str(user_id),
                session_id=str(session_id),
                query=message,
            )
        except Exception as e:
            logger.warning("Memory retrieval failed", error=str(e))
            memory_context = ""

        # 4. Get RAG context
        try:
            rag_context = await self.rag_pipeline.retrieve(
                query=message, user_id=str(user_id)
            )
        except Exception as e:
            logger.warning("RAG retrieval failed", error=str(e))
            rag_context = ""

        # 5. Get recent chat history for context
        recent_messages = await self.message_repo.get_recent_messages(
            db, session_id, limit=10
        )
        chat_history = []
        for msg in recent_messages:
            if msg.role in ("user", "assistant"):
                chat_history.append({"role": msg.role, "content": msg.content})

        # 6 & 7 & 8. Stream from Groq via unified llm_service
        # (Pass the query, retrieved RAG context, and chat history)
        full_response = ""
        retrieval_latency = time.time() - start_time

        # Send metadata event
        yield f"data: {json.dumps({'event': 'metadata', 'data': {'retrieval_latency_ms': round(retrieval_latency * 1000, 2), 'session_id': str(session_id)}})}\n\n"

        try:
            token_stream = llm_service.stream_chat_response(
                query=message,
                context=rag_context,
                chat_history=chat_history[:-1] if chat_history else None,
                is_sse=False
            )
            async for token in token_stream:
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
        except Exception as e:
            logger.error("Groq streaming error", error=str(e))
            yield f"data: {json.dumps({'event': 'error', 'data': 'Stream interrupted'})}\n\n"
            return

        # 9. Save assistant response to DB
        total_latency = time.time() - start_time
        await self.message_repo.create_message(
            db=db,
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=full_response,
            metadata_json={
                "retrieval_latency_ms": round(retrieval_latency * 1000, 2),
                "total_latency_ms": round(total_latency * 1000, 2),
            },
            token_count=len(full_response.split()),
        )

        # 10. Update STM with this exchange
        try:
            await self.memory_orchestrator.store_exchange(
                user_id=str(user_id),
                session_id=str(session_id),
                user_message=message,
                assistant_response=full_response,
            )
        except Exception as e:
            logger.warning("Memory store failed", error=str(e))

        # 11. Generate follow-up questions
        try:
            follow_ups = await self.followup_service.generate_followups(
                query=message,
                response=full_response,
                context=rag_context[:500],
            )
            yield f"data: {json.dumps({'event': 'follow_up', 'data': follow_ups})}\n\n"
        except Exception as e:
            logger.warning("Follow-up generation failed", error=str(e))

        # 12. Send done event
        yield f"data: {json.dumps({'event': 'done', 'data': {'total_latency_ms': round(total_latency * 1000, 2)}})}\n\n"

        # 13. Emit QStash events (fire and forget)
        try:
            await qstash_producer.send_event(
                topic=QStashTopics.CHAT_MESSAGE_SENT,
                key=str(session_id),
                value={
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "role": "user",
                    "content_length": len(message),
                },
            )
            await qstash_producer.send_event(
                topic=QStashTopics.LLM_RESPONSE_GENERATED,
                key=str(session_id),
                value={
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "response_length": len(full_response),
                    "latency_ms": round(total_latency * 1000, 2),
                },
            )
        except Exception:
            pass

    def _build_system_prompt(self, query: str, rag_context: str, memory_context: str) -> str:
        is_resume_request = any(
            kw in query.lower() for kw in [
                "resume", "cv", "portfolio", "all you know", "everything about", 
                "entire profile", "full profile", "all details", "who is aquib"
            ]
        )

        parts = [
            "You are Peanut AI.",
            "You are an AI portfolio assistant for Aquib Younis.",
            "Your purpose is to help users understand Aquib's projects, AI engineering work, backend systems, internships, technologies, experience, and resume information.",
            "",
            "STRICT RULES:",
            "- ONLY answer using provided context",
            "- NEVER invent information",
            "- NEVER hallucinate fake projects or technologies",
            "- If information is unavailable, respond: 'I do not have that information yet.'",
            "",
        ]

        if is_resume_request:
            parts.append(
                "CRITICAL FORMATTING INSTRUCTION FOR RESUME/PORTFOLIO OVERVIEW REQUESTS:\n"
                "- Whenever the user asks for Aquib's \"resume\", \"cv\", \"portfolio\", \"about you\", or a complete overview of his profile, you MUST format the response in a highly-visual, infographic \"Card\" style using Markdown blockquotes (`>`).\n"
                "- Standard HTML inside ReactMarkdown is not fully parsed except for simple elements, so you MUST use Markdown blockquotes (`>`) to represent cards. In your CSS/Renderer, blockquotes are styled as premium glass cards with a red border, making them look fantastic.\n"
                "- Each blockquote block MUST act as a single card for a specific category (e.g. About Card, Skills Card, Project Cards, Experience Card, Contact Card, Links Card).\n"
                "- Centering text must be simulated using clean markdown structures, bold headings, and emojis.\n"
                "    \n"
                "Structure the \"Resume\" response exactly like this:\n"
                "\n"
                "    # 💼 PULA AQUIB YOUNIS\n"
                "    **AI Systems Engineer & Backend Architect**  \n"
                "    📍 Bangalore, Karnataka, India | ✉️ aquibyounis1@gmail.com | 🌐 [LinkedIn](https://linkedin.com/in/aquib-younis) | 💻 [GitHub](https://github.com/aquibyounis)\n"
                "\n"
                "    ---\n"
                "\n"
                "    > ### 👤 **About Card**\n"
                "    > **Pula Aquib Younis** is a highly passionate AI Systems Engineer and Computer Science student at VIT-AP. He specializes in building robust Semantic RAG systems, local LLM orchestrations, multi-agent frameworks, and high-performance backend architectures. He is dedicated to bridging the gap between AI capability and clean engineering.\n"
            )
        else:
            parts.append(
                "CRITICAL FORMATTING INSTRUCTION FOR TARGETED QUESTIONS:\n"
                "- The user is asking a specific, targeted question (e.g. about only projects, or education, or background).\n"
                "- Do NOT output the full resume or the card-based infographic format with all sections.\n"
                "- Provide a direct, professional, conversational, and beautifully formatted answer to their specific question using the provided knowledge context.\n"
                "- If appropriate, you may format your answer as a single blockquote card (e.g. if asked about a specific project, show only that project's card).\n"
            )

        if is_resume_request:
            parts.append(
                "    > ### 🛠️ **Technical Skills Card**\n"
                "    > * **AI & LLM Orchestration**: Semantic RAG Pipelines, LangChain, LangGraph, Ollama, Qdrant Vector DB, ChromaDB\n"
                "    > * **Backend Development**: FastAPI, Node.js, Express.js, WebSockets, RESTful APIs\n"
                "    > * **Languages**: Python, JavaScript, SQL, Bash\n"
                "    > * **Databases & Caching**: PostgreSQL (SQLAlchemy), Redis, MongoDB, MERN Stack\n"
                "    > * **Infrastructure & Tools**: Git, Docker, Docker Compose, Linux, Alembic Migrations\n"
                "\n"
                "    > ### 🚀 **Project Card: Commander NOVA**\n"
                "    > * **Role**: AI Systems Developer (2025)\n"
                "    > * **Summary**: AI-powered virtual astronaut assistant for futuristic mission assistance using LangChain and ChromaDB.\n"
                "    > * **Key Work**: Built RAG-based space mission reasoning workflows, semantic context retrieval, and integrated FastAPI backend.\n"
                "    > * **Tech Stack**: Python, LangChain, ChromaDB, FastAPI, LLMs\n"
                "\n"
                "    > ### 🚀 **Project Card: Fresher Nav**\n"
                "    > * **Role**: Full-Stack Engineer (2025)\n"
                "    > * **Summary**: A smart navigation and resource search assistant for freshmen, integrating a custom RAG-powered vector search engine to query campus documents in real-time.\n"
                "    > * **Tech Stack**: Node.js, Express, Qdrant Vector DB, React\n"
                "\n"
                "    > ### 🚀 **Project Card: AI Sales Call Intelligence**\n"
                "    > * **Role**: AI Systems Intern (2025)\n"
                "    > * **Summary**: Automated pipeline to transcribe, analyze, and generate actionable insights and sentiment scores from enterprise sales calls.\n"
                "    > * **Tech Stack**: Python, OpenAI Whisper, GPT-4, FastAPI\n"
                "\n"
                "    > ### 💼 **Experience Card: SmartBridge**\n"
                "    > * **Role**: Full Stack MERN Intern (2024)\n"
                "    > * **Summary**: Developed responsive React components, integrated Express/Node APIs, improved MongoDB synchronization workflows, and worked in Agile MVP delivery.\n"
                "\n"
                "    > ### 🎓 **Education Card: VIT-AP University**\n"
                "    > * **Degree**: B.Tech in Computer Science and Engineering (CSE)\n"
                "    > * **Focus**: AI Systems Engineering, Distributed Databases, and Software Architecture\n"
                "\n"
                "    > ### 📞 **Contact Card**\n"
                "    > * **Email**: aquibyounis1@gmail.com\n"
                "    > * **Location**: Bangalore, Karnataka, India\n"
                "    > * **Action**: Drop a message directly by typing `connect` in this chat!\n"
                "\n"
                "    > ### 🔗 **Quick Links Card**\n"
                "    > * **LinkedIn**: [linkedin.com/in/aquib-younis](https://linkedin.com/in/aquib-younis)\n"
                "    > * **GitHub**: [github.com/aquibyounis](https://github.com/aquibyounis)\n"
                "    > * **Portfolio**: [aquibyounis.com](https://aquibyounis.com)\n"
                "\n"
                "    ---\n"
            )

        parts.append(
            "RESPONSE FORMAT:\n"
            "- Use markdown with headings and bullet points\n"
            "- Keep responses concise and professional"
        )

        if memory_context:
            parts.append(f"\nCONVERSATION MEMORY:\n{memory_context}")

        if rag_context:
            parts.append(f"\nKNOWLEDGE CONTEXT:\n{rag_context}")

        return "\n".join(parts)
