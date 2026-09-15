# ============================================================
# IGNYX AI BACKEND
# FastAPI + Google Gemini + Exa + SQLite
# Streaming + Conversations + Memory + Web Search
# ============================================================


import json
import os
import ast
import operator
import re
import time

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


from dotenv import load_dotenv


from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
)


from fastapi.middleware.cors import (
    CORSMiddleware,
)


from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)


from pydantic import (
    BaseModel,
    Field,
)


from sqlalchemy.orm import (
    Session,
)


from google import genai
from google.genai import types


from exa_py import Exa


from database import (
    Base,
    engine,
    SessionLocal,
)


from models import (
    Conversation,
    Message,
)

from memory.models import Memory
from memory.manager import (
    DEFAULT_USER_KEY,
    create_memory,
    get_all_memories,
    update_memory,
    delete_memory,
    clear_memories,
)
from memory.retriever import retrieve_memory_context
from memory.extractor import extract_memories


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "IGNYX AI"

APP_VERSION = "5.2.1"


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


EXA_API_KEY = os.getenv(
    "EXA_API_KEY"
)


MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3-flash-preview",
).strip()


MAX_MESSAGE_LENGTH = 10000

MAX_HISTORY_MESSAGES = 12

MAX_OUTPUT_TOKENS = 4096

MAX_SEARCH_RESULTS = 3

# Gemini transient availability handling.
GEMINI_MAX_RETRIES = 0
GEMINI_RETRY_DELAYS = ()
GEMINI_FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-3.1-flash-lite",
).strip()


# ============================================================
# VALIDATE GEMINI API KEY
# ============================================================

if not GEMINI_API_KEY:

    raise RuntimeError(

        "\n\n"
        "GEMINI_API_KEY is missing.\n\n"
        "Create backend/.env and add:\n\n"
        "GEMINI_API_KEY=your_actual_api_key\n"
        "GEMINI_MODEL=gemini-3-flash-preview\n"

    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=1,
        )
    ),
)


# ============================================================
# EXA CLIENT
# ============================================================

exa_client = None


if EXA_API_KEY:

    try:

        exa_client = Exa(
            api_key=EXA_API_KEY
        )

        print(
            "EXA: Client initialized successfully."
        )

    except Exception as error:

        print(
            "EXA INITIALIZATION ERROR:",
            str(error)
        )

        exa_client = None


else:

    print(
        "WARNING: EXA_API_KEY not found. "
        "Web search will be unavailable."
    )


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print()
    print("=" * 60)
    print("🔥 IGNYX AI BACKEND STARTED")
    print("=" * 60)
    print("API Docs: http://127.0.0.1:8000/docs")
    print("Health Check: http://127.0.0.1:8000/health")
    print(f"Gemini Model: {MODEL_NAME}")
    print("Database: Connected")
    print("Streaming: Enabled")
    print("Conversation Memory: Enabled")
    print("Calculator: Enabled")
    print("Web Search Provider: Exa")
    print("Exa Search: " + ("Enabled" if exa_client else "Disabled"))
    print("=" * 60)
    print()

    yield

    print()
    print("🔥 IGNYX AI BACKEND STOPPED")
    print()


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(

    title="IGNYX AI API",

    description=(
        "IGNYX AI Assistant powered by "
        "Google Gemini and Exa Search"
    ),

    version=APP_VERSION,

    lifespan=lifespan,

)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:3000",

        "http://127.0.0.1:3000",

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
    )

    conversation_id: Optional[int] = None

    web_search: Optional[bool] = False

    user_key: str = Field(
        default=DEFAULT_USER_KEY,
        min_length=1,
        max_length=100,
    )


class ConversationRequest(BaseModel):

    title: Optional[str] = (
        "New Conversation"
    )


class UpdateConversationRequest(BaseModel):

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )


# ============================================================
# IGNYX SYSTEM PROMPT
# ============================================================

IGNYX_INSTRUCTIONS = """

You are IGNYX AI.

IGNYX stands for advanced intelligent
artificial intelligence assistance.

You are:

- Professional
- Intelligent
- Friendly
- Helpful
- Conversational
- Clear
- Accurate

Your purpose is to help users with:

- Artificial Intelligence
- Machine Learning
- Deep Learning
- Data Science
- Data Analysis
- Python
- Programming
- Web Development
- FastAPI
- JavaScript
- TypeScript
- SQL
- Generative AI
- Large Language Models
- RAG
- AI Agents
- Mathematics
- Research
- Career Guidance
- Resume Development
- Job Applications
- Software Engineering
- Technical Projects

Response rules:

- Answer the user's actual question.
- Never give the same generic introduction repeatedly.
- Do not introduce yourself unless appropriate.
- Be conversational.
- Use Markdown when useful.
- Use headings for longer answers.
- Use bullet points when useful.
- Use code blocks for programming.
- Give complete working code when requested.
- Explain dependencies when necessary.
- Explain how to run code when useful.
- Do not invent facts.
- Do not invent sources.
- If uncertain, say so.
- Keep simple answers concise.
- Give detailed technical explanations when requested.

IMPORTANT CURRENT INFORMATION RULE:

When web search context is provided:

- Treat the web search context as newer than your internal knowledge.
- Prioritize reliable information from the provided web context.
- Do not answer using outdated internal knowledge when reliable web search information is available.
- Carefully distinguish official announcements from rumors, speculation, leaks, predictions, and unofficial information.
- Never present rumors or speculation as confirmed facts.
- For new products, AI models, software versions, companies, technology releases, or announcements, clearly state whether the information is officially confirmed.
- If search results conflict, mention the uncertainty clearly.
- Do not invent URLs.
- Do not invent sources.
- Only mention sources that exist in the provided web context.
- Give a clear and direct answer based on the available evidence.

SOURCE QUALITY RULE:

When discussing technology companies or AI products:

- Prefer official company information when available.
- Prefer official announcements over third-party speculation.
- Clearly label unofficial reports as unofficial.
- If something cannot be confirmed, say that it cannot currently be confirmed.

Programming rules:

- Write clean code.
- Use modern best practices.
- Include imports.
- Mention installation commands.
- Explain important sections.
- Do not provide broken examples intentionally.

Always behave as IGNYX AI.

"""



# ============================================================
# AI ROUTER
# ============================================================

def route_message(message: str) -> Dict[str, Any]:
    """
    Deterministic first-pass task router.

    The router selects a capability; Gemini remains responsible for
    generating the final natural-language answer.
    """

    text = message.strip()
    lowered = text.lower()

    code_markers = (
        "```", "traceback", "syntaxerror", "typeerror", "exception",
        "stack trace", "debug this", "debug the code", "fix this code",
        "fix my code", "write code", "generate code", "implement",
        "refactor", "function", "class ", "api endpoint", "fastapi",
        "flask", "django", "javascript", "typescript", "python", "sql",
        "powershell", "bash script", "shell script", "react", "next.js",
        "nextjs", "node.js", "nodejs", "html", "css", "git", "github",
    )

    writing_markers = (
        "write an email", "write a mail", "draft an email", "draft a mail",
        "cover letter", "resume", "cv", "linkedin", "rewrite this",
        "rephrase this", "proofread", "grammar", "make this professional",
        "make it professional", "caption", "blog post", "article", "essay",
        "statement of purpose",
    )

    analysis_markers = (
        "analyze", "analyse", "analysis", "compare", "comparison", "evaluate",
        "break down", "insights", "pros and cons",
        "advantages and disadvantages", "explain the difference",
        "interpret", "review this",
    )

    research_markers = (
        "research", "search the web", "search online", "search internet",
        "look up", "lookup", "browse", "find online", "find latest",
        "latest", "today", "current", "currently", "recent", "news",
        "breaking", "trending", "announcement", "announced", "released",
        "release", "launch", "launched", "this week", "this month",
    )

    # Calculator is checked first so simple math never reaches Gemini.
    if calculate_from_message(message) is not None:
        return {
            "intent": "calculator",
            "confidence": 0.99,
            "reason": "The message contains a safely evaluable mathematical expression.",
            "tools": ["calculator"],
        }

    if any(marker in lowered for marker in research_markers):
        return {
            "intent": "web_search",
            "confidence": 0.92,
            "reason": "The message asks for current, recent, online, or research-oriented information.",
            "tools": ["web_search"],
        }

    if any(marker in lowered for marker in code_markers):
        return {
            "intent": "coding",
            "confidence": 0.90,
            "reason": "The message contains programming, debugging, or software-engineering signals.",
            "tools": [],
        }

    if any(marker in lowered for marker in writing_markers):
        return {
            "intent": "writing",
            "confidence": 0.88,
            "reason": "The message requests drafting, rewriting, editing, or professional writing.",
            "tools": [],
        }

    if any(marker in lowered for marker in analysis_markers):
        return {
            "intent": "analysis",
            "confidence": 0.86,
            "reason": "The message asks for comparison, evaluation, interpretation, or deeper analysis.",
            "tools": [],
        }

    return {
        "intent": "general_chat",
        "confidence": 0.72,
        "reason": "No specialized task pattern was strong enough to select another route.",
        "tools": [],
    }


def route_instruction(route: Dict[str, Any]) -> str:
    """Return focused instructions for the selected task mode."""

    instructions = {
        "calculator": (
            "TASK MODE: CALCULATOR. "
            "Use the exact evaluated result supplied by IGNYX. "
            "Do not approximate or silently recalculate it."
        ),
        "web_search": (
            "TASK MODE: WEB RESEARCH. "
            "Prioritize the provided web context. Distinguish confirmed facts "
            "from speculation and mention only sources supplied by IGNYX."
        ),
        "coding": (
            "TASK MODE: SOFTWARE ENGINEERING. "
            "When code is requested, provide complete working code with imports. "
            "Use the correct Markdown language tag for code fences and include "
            "installation/run/test commands when useful."
        ),
        "writing": (
            "TASK MODE: WRITING. "
            "Follow the requested tone, audience, format, and length. "
            "Return polished copy that is ready to use."
        ),
        "analysis": (
            "TASK MODE: ANALYSIS. "
            "Structure the reasoning clearly, state assumptions when relevant, "
            "and separate evidence from inference."
        ),
        "general_chat": (
            "TASK MODE: GENERAL ASSISTANCE. "
            "Answer directly and naturally without unnecessary framing."
        ),
    }

    return instructions.get(
        route.get("intent", "general_chat"),
        instructions["general_chat"],
    )


# ============================================================
# SAFE CALCULATOR
# ============================================================

SAFE_OPERATORS = {

    ast.Add: operator.add,

    ast.Sub: operator.sub,

    ast.Mult: operator.mul,

    ast.Div: operator.truediv,

    ast.FloorDiv: operator.floordiv,

    ast.Mod: operator.mod,

    ast.Pow: operator.pow,

    ast.USub: operator.neg,

    ast.UAdd: operator.pos,

}


def safe_calculate(
    expression: str,
):

    if len(expression) > 100:

        raise ValueError(
            "Expression is too long."
        )


    tree = ast.parse(
        expression,
        mode="eval",
    )


    def evaluate(node):


        # NUMBERS

        if isinstance(
            node,
            ast.Constant,
        ):

            if isinstance(
                node.value,
                (int, float),
            ):

                return node.value


            raise ValueError(
                "Invalid value."
            )


        # BINARY OPERATIONS

        if isinstance(
            node,
            ast.BinOp,
        ):

            operator_type = type(
                node.op
            )


            if (
                operator_type
                not in SAFE_OPERATORS
            ):

                raise ValueError(
                    "Invalid operator."
                )


            left = evaluate(
                node.left
            )

            right = evaluate(
                node.right
            )


            if isinstance(
                node.op,
                (
                    ast.Div,
                    ast.FloorDiv,
                    ast.Mod,
                ),
            ):

                if right == 0:

                    raise ValueError(
                        "Division by zero."
                    )


            if isinstance(
                node.op,
                ast.Pow,
            ):

                if abs(right) > 100:

                    raise ValueError(
                        "Exponent too large."
                    )


            return SAFE_OPERATORS[
                operator_type
            ](
                left,
                right,
            )


        # UNARY OPERATIONS

        if isinstance(
            node,
            ast.UnaryOp,
        ):

            operator_type = type(
                node.op
            )


            if (
                operator_type
                not in SAFE_OPERATORS
            ):

                raise ValueError(
                    "Invalid operator."
                )


            return SAFE_OPERATORS[
                operator_type
            ](
                evaluate(
                    node.operand
                )
            )


        raise ValueError(
            "Invalid expression."
        )


    return evaluate(
        tree.body
    )


# ============================================================
# CALCULATOR DETECTION
# ============================================================

def calculate_from_message(
    message: str,
):

    text = message.strip()

    cleaned = text.lower()


    cleaned = re.sub(

        r"^(calculate|solve|compute|what is|find)\s*",

        "",

        cleaned,

    )


    cleaned = cleaned.strip()


    cleaned = cleaned.replace(
        "×",
        "*",
    )

    cleaned = cleaned.replace(
        "÷",
        "/",
    )

    cleaned = cleaned.replace(
        "^",
        "**",
    )


    if not cleaned:

        return None


    allowed_pattern = (

        r"[0-9\s\+\-\*\/\.\(\)%]+"

    )


    if not re.fullmatch(
        allowed_pattern,
        cleaned,
    ):

        return None


    try:

        result = safe_calculate(
            cleaned
        )


        return {

            "expression": cleaned,

            "result": result,

        }


    except Exception:

        return None


# ============================================================
# EXA SEARCH
# ============================================================

def search_exa(
    query: str,
    max_results: int = MAX_SEARCH_RESULTS,
) -> List[Dict[str, Any]]:


    if not exa_client:

        raise RuntimeError(
            "Exa Search is not configured. "
            "Please check EXA_API_KEY in .env."
        )


    try:

        print()

        print(
            "=" * 60
        )

        print(
            "EXA WEB SEARCH"
        )

        print(
            "Query:",
            query
        )

        print(
            "=" * 60
        )


        response = exa_client.search_and_contents(

            query=query,

            type="auto",

            num_results=max_results,

            text=True,

        )


        sources = []


        for result in response.results:

            title = getattr(
                result,
                "title",
                None,
            ) or "Untitled Source"


            url = getattr(
                result,
                "url",
                None,
            ) or ""


            text_content = getattr(
                result,
                "text",
                None,
            ) or ""


            # Limit content to prevent
            # excessively large Gemini prompts.

            if len(text_content) > 2500:

                text_content = (
                    text_content[:2500]
                    + "\n..."
                )


            sources.append({

                "title": title,

                "url": url,

                "content": text_content,

            })


        print(
            f"EXA RESULTS: {len(sources)}"
        )

        print()


        return sources


    except Exception as error:

        print()

        print(
            "=" * 60
        )

        print(
            "EXA SEARCH ERROR"
        )

        print(
            str(error)
        )

        print(
            "=" * 60
        )

        print()


        raise RuntimeError(
            f"Exa Search Error: {str(error)}"
        )


# ============================================================
# BUILD WEB CONTEXT
# ============================================================

def build_web_context(
    sources: List[Dict[str, Any]],
) -> str:


    if not sources:

        return ""


    context = (

        "\n\n"
        "WEB SEARCH CONTEXT:\n"
        "The following information was retrieved "
        "using Exa Search.\n"
        "Use this information to answer the user.\n"
        "Do not invent sources or URLs.\n\n"

    )


    for index, source in enumerate(
        sources,
        start=1,
    ):

        context += (

            f"\nSOURCE {index}\n"

            f"TITLE: {source['title']}\n"

            f"URL: {source['url']}\n"

            f"CONTENT:\n"

            f"{source['content']}\n"

            "\n"

            + "-" * 50

            + "\n"

        )


    return context


# ============================================================
# AUTO WEB SEARCH DETECTION
# ============================================================

def should_auto_search(
    message: str,
) -> bool:

    text = message.lower().strip()

    explicit_patterns = [
        "search web", "search the web", "search online",
        "search internet", "look up", "lookup", "find online",
        "find information", "google", "research", "browse",
        "search for", "find latest",
    ]

    current_patterns = [
        "latest", "today", "current", "currently", "recent",
        "recently", "new", "news", "update", "updates",
        "this week", "this month", "this year", "2025", "2026",
        "2027", "released", "release", "launch", "launched",
        "announcement", "announced", "breaking", "trending",
    ]

    technology_patterns = [
        "chatgpt", "openai", "gpt-4", "gpt-4o", "gpt-5",
        "gpt-6", "sora", "codex", "gemini", "google ai",
        "deepmind", "project astra", "astra", "claude",
        "anthropic", "grok", "perplexity", "llama", "mistral",
        "copilot", "deepseek", "qwen", "ai model", "ai models",
        "ai agent", "ai agents", "llm", "large language model",
    ]

    company_patterns = [
        "company", "companies", "startup", "startups", "product",
        "products", "platform", "service", "pricing", "price",
        "valuation", "funding", "acquisition", "ceo", "founder",
    ]

    career_patterns = [
        "job openings", "jobs available", "latest jobs", "hiring",
        "currently hiring", "career opportunities", "job vacancy",
        "vacancies", "internship openings", "fresher jobs",
    ]

    all_patterns = (
        explicit_patterns
        + current_patterns
        + technology_patterns
        + company_patterns
        + career_patterns
    )

    for pattern in all_patterns:
        if pattern in text:
            print()
            print("=" * 60)
            print("🔍 AUTO WEB SEARCH TRIGGERED")
            print("Pattern:", pattern)
            print("Message:", message)
            print("=" * 60)
            print()
            return True

    return False


# ============================================================
# CLEAN SOURCES FOR FRONTEND
# ============================================================

def clean_sources(
    sources: List[Dict[str, Any]],
) -> List[Dict[str, str]]:


    cleaned_sources = []


    seen_urls = set()


    for source in sources:


        url = source.get(
            "url",
            ""
        )


        if not url:

            continue


        if url in seen_urls:

            continue


        seen_urls.add(
            url
        )


        cleaned_sources.append({

            "title": source.get(
                "title",
                "Source",
            ),

            "url": url,

        })


    return cleaned_sources


# ============================================================
# DATABASE HELPERS
# ============================================================

def commit_database(
    db: Session,
):

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise


# ============================================================
# CREATE CONVERSATION
# ============================================================

def create_conversation(

    db: Session,

    title: str,

):

    clean_title = (

        title.strip()

        or "New Conversation"

    )


    if len(clean_title) > 60:

        clean_title = (

            clean_title[:60].rstrip()

            + "..."

        )


    conversation = Conversation(

        title=clean_title,

        created_at=datetime.now(timezone.utc),

        updated_at=datetime.now(timezone.utc),

    )


    db.add(
        conversation
    )


    commit_database(
        db
    )


    db.refresh(
        conversation
    )


    return conversation


# ============================================================
# GET OR CREATE CONVERSATION
# ============================================================

def get_or_create_conversation(

    db: Session,

    conversation_id: Optional[int],

    first_message: str,

):


    if conversation_id:

        conversation = (

            db.query(
                Conversation
            )

            .filter(
                Conversation.id
                == conversation_id
            )

            .first()

        )


        if conversation:

            return conversation


    return create_conversation(

        db,

        first_message,

    )


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(

    db: Session,

    conversation_id: int,

    role: str,

    content: str,

):


    message = Message(

        conversation_id=conversation_id,

        role=role,

        content=content,

        created_at=datetime.now(timezone.utc),

    )


    db.add(
        message
    )


    conversation = (

        db.query(
            Conversation
        )

        .filter(
            Conversation.id
            == conversation_id
        )

        .first()

    )


    if conversation:

        conversation.updated_at = (

            datetime.now(timezone.utc)

        )


    commit_database(
        db
    )


    return message


# ============================================================
# GET CONVERSATION HISTORY
# ============================================================

def get_conversation_history(

    db: Session,

    conversation_id: int,

):


    messages = (

        db.query(
            Message
        )

        .filter(
            Message.conversation_id
            == conversation_id
        )

        .order_by(
            Message.created_at.asc()
        )

        .all()

    )


    messages = messages[
        -MAX_HISTORY_MESSAGES:
    ]


    history = []


    for message in messages:

        role = (

            "user"

            if message.role == "user"

            else "model"

        )


        history.append({

            "role": role,

            "content":
                message.content,

        })


    return history


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(

    user_message: str,

    history,

    web_context: str = "",

    route: Optional[Dict[str, Any]] = None,

    memory_context: str = "",

):

    conversation_text = ""

    if history:
        conversation_text += (
            "\n\n"
            "CONVERSATION HISTORY:\n"
        )

        for item in history:
            role = (
                "USER"
                if item["role"] == "user"
                else "IGNYX"
            )

            conversation_text += (
                f"\n{role}: "
                f"{item['content']}\n"
            )

    active_route = route or {
        "intent": "general_chat",
        "confidence": 0.72,
        "reason": "Default route",
        "tools": [],
    }

    prompt = (
        IGNYX_INSTRUCTIONS
        + "\n\n"
        + "ROUTING DECISION:\n"
        + f"Intent: {active_route.get('intent', 'general_chat')}\n"
        + f"Confidence: {active_route.get('confidence', 0):.2f}\n"
        + f"Reason: {active_route.get('reason', '')}\n"
        + route_instruction(active_route)
        + memory_context
        + conversation_text
        + web_context
        + "\n\n"
        + "CURRENT USER MESSAGE:\n"
        + user_message
        + "\n\n"
        + "Respond naturally to the current user message."
    )

    return prompt


# ============================================================
# MEMORY ENGINE HELPERS
# ============================================================

def save_extracted_memories(
    db: Session,
    message: str,
    user_key: str = DEFAULT_USER_KEY,
) -> List[Dict[str, Any]]:
    """Extract useful memories from the message and persist them."""

    extracted = extract_memories(message)
    saved: List[Dict[str, Any]] = []

    for item in extracted:
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()

        if not key or not value:
            continue

        try:
            memory = create_memory(
                db=db,
                key=key,
                value=value,
                category=str(item.get("category", "general")),
                importance=float(item.get("importance", 0.5)),
                user_key=user_key,
            )

            saved.append({
                "id": memory.id,
                "key": memory.key,
                "value": memory.value,
                "category": memory.category,
                "importance": memory.importance,
            })
        except Exception as error:
            print("MEMORY SAVE WARNING:", str(error))

    return saved


def memory_response(memory: Memory) -> Dict[str, Any]:
    return {
        "id": memory.id,
        "user_key": memory.user_key,
        "category": memory.category,
        "key": memory.key,
        "value": memory.value,
        "importance": memory.importance,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


# ============================================================
# GENERATE GEMINI RESPONSE
# ============================================================


def is_gemini_quota_error(error: Exception) -> bool:
    """
    Detect Gemini quota/rate-limit exhaustion.

    Gemini commonly reports these failures as HTTP 429 RESOURCE_EXHAUSTED.
    We handle quota errors separately so we do not waste another request
    against a second Gemini model in the same project.
    """

    error_text = str(error).lower()

    quota_markers = (
        "429 resource_exhausted",
        "resource_exhausted",
        "too many requests",
        "quota exceeded",
        "quotaexceeded",
        "generaterequestsperdayperproject-freetier",
        "generativelanguage.googleapis.com/generate_content_free_tier_requests",
        "ratelimit",
        "rate limit",
    )

    return any(
        marker in error_text
        for marker in quota_markers
    )


def is_gemini_busy_error(error: Exception) -> bool:
    """
    Detect transient Gemini availability / overload errors.

    Quota errors are intentionally excluded because a fallback Gemini model
    in the same project may consume the same project-level quota.
    """

    error_text = str(error).lower()

    if is_gemini_quota_error(error):
        return False

    busy_markers = (
        "503",
        "unavailable",
        "high demand",
        "service unavailable",
        "temporarily unavailable",
        "overloaded",
    )

    return any(
        marker in error_text
        for marker in busy_markers
    )


class GeminiQuotaError(RuntimeError):
    """Raised when the Gemini project quota has been exhausted."""

    def __init__(
        self,
        message: str = (
            "Gemini API quota has been exhausted for the current free-tier "
            "period. Please wait for the quota to reset before trying again."
        ),
    ):
        super().__init__(message)


class GeminiBusyError(RuntimeError):
    """Raised when Gemini remains unavailable after all retries."""

    def __init__(
        self,
        message: str = (
            "IGNYX AI is experiencing high demand. "
            "Please try again in a moment."
        ),
    ):
        super().__init__(message)


def _gemini_config(model_name: str):
    """Return a low-latency Gemini generation config."""

    config_kwargs = {
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }

    # Gemini 3 Flash-family models support thinking_level.
    # Minimal is appropriate for normal chat and keeps first-token latency low.
    if any(
        marker in model_name
        for marker in (
            "gemini-3-flash",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.1-flash-lite",
        )
    ):
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level="minimal"
        )

    return types.GenerateContentConfig(**config_kwargs)


def _call_gemini(model_name: str, prompt: str):
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=_gemini_config(model_name),
    )

    text = getattr(response, "text", None)

    if text:
        return text.strip()

    raise RuntimeError(
        "Gemini returned an empty response."
    )


def generate_ai_response(prompt: str):
    """
    Fast Gemini path:
    1. Try the configured model once.
    2. If the configured model is quota-exhausted, stop immediately and
       surface a clear quota message instead of making another Gemini request.
    3. On a transient 503/overload, immediately switch to the low-latency
       fallback model.
    4. If all transient models are unavailable, surface a structured busy error.
    """

    models_to_try = [MODEL_NAME]

    if (
        GEMINI_FALLBACK_MODEL
        and GEMINI_FALLBACK_MODEL != MODEL_NAME
    ):
        models_to_try.append(
            GEMINI_FALLBACK_MODEL
        )

    for index, model_name in enumerate(
        models_to_try
    ):
        try:
            print(
                f"GEMINI REQUEST: {model_name}"
            )
            return _call_gemini(
                model_name,
                prompt,
            )

        except Exception as error:
            error_text = str(error)

            print()
            print("=" * 60)
            print("GEMINI ERROR")
            print(
                f"Model: {model_name}"
            )
            print(error_text)
            print("=" * 60)
            print()

            # Do not call another Gemini model when the project quota is
            # exhausted. Both models may share the same project quota.
            if is_gemini_quota_error(error):
                raise GeminiQuotaError() from error

            if not is_gemini_busy_error(error):
                raise RuntimeError(
                    error_text
                ) from error

            # Immediately fail over only for transient service availability.
            if index + 1 < len(models_to_try):
                print(
                    "GEMINI BUSY: immediate fallback -> "
                    f"{models_to_try[index + 1]}"
                )
                continue

            print(
                "GEMINI BUSY: all configured models unavailable."
            )
            raise GeminiBusyError() from error

    raise GeminiBusyError()


# ============================================================
# SSE EVENT
# ============================================================

def sse_event(
    data,
):

    return (

        "data: "

        + json.dumps(
            data
        )

        + "\n\n"

    )


# ============================================================
# SPLIT TEXT
# ============================================================

def split_text(
    text: str,
):


    chunk_size = 20


    for index in range(

        0,

        len(text),

        chunk_size,

    ):

        yield text[
            index:
            index + chunk_size
        ]


# ============================================================
# STREAM RESPONSE
# ============================================================

def stream_response(
    request: ChatRequest,
):


    db = SessionLocal()


    try:


        user_message = (
            request.message.strip()
        )


        if not user_message:

            yield sse_event({

                "type": "error",

                "message":
                    "Please enter a message.",

            })

            return


        # ================================================
        # ================================================
        # AI ROUTER
        # ================================================

        route = route_message(user_message)

        user_key = (
            request.user_key.strip()
            or DEFAULT_USER_KEY
        )

        memory_result = retrieve_memory_context(
            db=db,
            query=user_message,
            user_key=user_key,
            limit=5,
        )

        memory_context = memory_result["context"]

        print()
        print("=" * 60)
        print("🧠 IGNYX AI ROUTER")
        print("Intent:", route["intent"])
        print("Confidence:", route["confidence"])
        print("Reason:", route["reason"])
        print("Tools:", ", ".join(route["tools"]) or "none")
        print("=" * 60)
        print()

        # GET CONVERSATION
        # ================================================

        conversation = (

            get_or_create_conversation(

                db,

                request.conversation_id,

                user_message,

            )

        )


        # ================================================
        # SAVE USER MESSAGE
        # ================================================

        save_message(

            db,

            conversation.id,

            "user",

            user_message,

        )


        # ================================================
        # CALCULATOR
        # ================================================

        calculation = (

            calculate_from_message(
                user_message
            )

        )


        if calculation:


            answer = (

                f"## Calculation Result\n\n"

                f"**Expression:** "

                f"`{calculation['expression']}`\n\n"

                f"**Result:** "

                f"`{calculation['result']}`"

            )


            save_message(

                db,

                conversation.id,

                "assistant",

                answer,

            )


            for chunk in split_text(
                answer
            ):

                yield sse_event({

                    "type": "delta",

                    "text": chunk,

                })


            yield sse_event({

                "type": "done",

                "conversation_id":
                    conversation.id,

                "web_search_used": False,

                "calculator_used": True,

                "intent": "calculator",

                "route_confidence": route["confidence"],

                "tools_used": route["tools"],

                "sources": [],

            })


            return


        # ================================================
        # HISTORY
        # ================================================

        history = (

            get_conversation_history(

                db,

                conversation.id,

            )

        )


        # Remove latest user message

        if history:

            history = history[:-1]


        # ================================================
        # WEB SEARCH DECISION
        # ================================================

        manual_web_search = bool(
            request.web_search
        )


        # The AI router controls automatic web-search selection.
        # The frontend may also explicitly enable web search.
        # Keyword-based auto-search is intentionally disabled here
        # so normal conversation and coding requests do not trigger Exa.
        use_web_search = (
            manual_web_search
            or route["intent"] == "web_search"
        )


        raw_sources = []


        web_context = ""


        # ================================================
        # EXA WEB SEARCH
        # ================================================

        if use_web_search:


            try:

                raw_sources = (

                    search_exa(
                        query=user_message,
                        max_results=MAX_SEARCH_RESULTS,
                    )

                )


                web_context = (

                    build_web_context(
                        raw_sources
                    )

                )


            except Exception as search_error:


                print()

                print(
                    "WEB SEARCH WARNING:"
                )

                print(
                    str(search_error)
                )

                print()


                raw_sources = []


                web_context = (

                    "\n\n"
                    "WEB SEARCH STATUS:\n"
                    "Web search was requested but "
                    "no search results were available.\n"

                )


        # ================================================
        # BUILD PROMPT
        # ================================================

        prompt = build_prompt(

            user_message,

            history,

            web_context,

            route,

            memory_context,

        )


        # ================================================
        # GENERATE RESPONSE
        # ================================================

        answer = generate_ai_response(
            prompt
        )


        # ================================================
        # STREAM TEXT
        # ================================================

        for chunk in split_text(
            answer
        ):

            yield sse_event({

                "type": "delta",

                "text": chunk,

            })


        # ================================================
        # SAVE AI MESSAGE
        # ================================================

        save_message(

            db,

            conversation.id,

            "assistant",

            answer,

        )

        saved_memories = save_extracted_memories(
            db=db,
            message=user_message,
            user_key=user_key,
        )


        # ================================================
        # CLEAN SOURCES
        # ================================================

        frontend_sources = (

            clean_sources(
                raw_sources
            )

        )


        # ================================================
        # DONE
        # ================================================

        yield sse_event({

            "type": "done",

            "conversation_id":
                conversation.id,

            "web_search_used":
                use_web_search,

            "calculator_used": False,

            "intent":
                route["intent"],

            "route_confidence":
                route["confidence"],

            "tools_used":
                route["tools"],

            "memory_used": memory_result["count"] > 0,

            "memories_saved": saved_memories,

            "memory_count": memory_result["count"],

            "sources":
                frontend_sources,

        })


    except GeminiQuotaError as error:

        error_message = str(error)

        print()
        print("IGNYX STREAM GEMINI QUOTA:")
        print(error_message)
        print()

        yield sse_event({
            "type": "error",
            "error": True,
            "error_type": "ai_quota_exceeded",
            "message": error_message,
        })


    except GeminiBusyError as error:

        error_message = str(error)

        print()
        print("IGNYX STREAM AI BUSY:")
        print(error_message)
        print()

        yield sse_event({
            "type": "error",
            "error": True,
            "error_type": "ai_busy",
            "message": error_message,
        })


    except Exception as error:

        error_message = str(error)

        print()
        print("IGNYX STREAM ERROR:")
        print(error_message)
        print()

        yield sse_event({
            "type": "error",
            "error": True,
            "error_type": "server_error",
            "message": (
                "IGNYX could not complete the request. "
                "Please try again."
            ),
        })
# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health"
)
def health():

    return {

        "status": "healthy",

        "service": APP_NAME,

        "version": APP_VERSION,

        "provider":
            "Google Gemini",

        "model":
            MODEL_NAME,

        "database":
            "connected",

        "exa_search":
            exa_client is not None,

        "features": {

            "chat": True,

            "streaming": True,

            "conversations": True,

            "memory": True,
            "long_term_memory": True,
            "context_retrieval": True,

            "calculator": True,

            "ai_router": True,

            "web_search":
                exa_client is not None,

            "sources":
                exa_client is not None,

        },

    }


# ============================================================
# AI ROUTER STATUS
# ============================================================

@app.post("/route")
def route_preview(
    request: ChatRequest,
):
    """
    Preview the routing decision without calling Gemini or Exa.
    Useful during development and debugging.
    """

    route = route_message(
        request.message.strip()
    )

    return {
        "message":
            request.message.strip(),

        "intent":
            route["intent"],

        "confidence":
            route["confidence"],

        "reason":
            route["reason"],

        "tools":
            route["tools"],

        "instruction":
            route_instruction(route),
    }


# ============================================================
# MEMORY API
# ============================================================


class MemoryCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=150)
    value: str = Field(..., min_length=1, max_length=5000)
    category: str = Field(default="general", min_length=1, max_length=50)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    user_key: str = Field(default=DEFAULT_USER_KEY, min_length=1, max_length=100)


class MemoryUpdateRequest(BaseModel):
    value: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    user_key: str = Field(default=DEFAULT_USER_KEY, min_length=1, max_length=100)


@app.get("/memory")
def list_memories(
    user_key: str = DEFAULT_USER_KEY,
    db: Session = Depends(get_db),
):
    memories = get_all_memories(db=db, user_key=user_key)
    return {
        "count": len(memories),
        "memories": [memory_response(memory) for memory in memories],
    }


@app.post("/memory")
def add_memory(
    request: MemoryCreateRequest,
    db: Session = Depends(get_db),
):
    memory = create_memory(
        db=db,
        key=request.key,
        value=request.value,
        category=request.category,
        importance=request.importance,
        user_key=request.user_key,
    )
    return {"success": True, "memory": memory_response(memory)}


@app.get("/memory/search")
def search_memories(
    q: str,
    user_key: str = DEFAULT_USER_KEY,
    db: Session = Depends(get_db),
):
    result = retrieve_memory_context(
        db=db,
        query=q,
        user_key=user_key,
        limit=10,
    )
    return {
        "query": q,
        "count": result["count"],
        "memories": [memory_response(memory) for memory in result["memories"]],
    }


@app.put("/memory/{memory_id}")
def edit_memory(
    memory_id: int,
    request: MemoryUpdateRequest,
    db: Session = Depends(get_db),
):
    memory = update_memory(
        db=db,
        memory_id=memory_id,
        value=request.value,
        category=request.category,
        importance=request.importance,
        user_key=request.user_key,
    )

    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return {"success": True, "memory": memory_response(memory)}


@app.delete("/memory/{memory_id}")
def remove_memory(
    memory_id: int,
    user_key: str = DEFAULT_USER_KEY,
    db: Session = Depends(get_db),
):
    deleted = delete_memory(db=db, memory_id=memory_id, user_key=user_key)

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return {"success": True, "message": "Memory deleted."}


@app.delete("/memory")
def remove_all_memories(
    user_key: str = DEFAULT_USER_KEY,
    db: Session = Depends(get_db),
):
    count = clear_memories(db=db, user_key=user_key)
    return {"success": True, "deleted": count}


@app.post("/memory/test")
def test_memory(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    user_key = request.user_key.strip() or DEFAULT_USER_KEY
    extracted = save_extracted_memories(
        db=db,
        message=request.message.strip(),
        user_key=user_key,
    )
    return {
        "success": True,
        "saved": bool(extracted),
        "memories": extracted,
    }


# ============================================================
# HOME
# ============================================================

@app.get("/")
def root():

    return {

        "name":
            "IGNYX AI API",

        "version":
            APP_VERSION,

        "status":
            "online",

        "model":
            MODEL_NAME,

        "search_provider":
            "Exa",

    }


# ============================================================
# TEST EXA SEARCH
# ============================================================

@app.get(
    "/search"
)
def test_search(
    q: str,
):


    if not q.strip():

        raise HTTPException(

            status_code=400,

            detail=(
                "Search query is required."
            ),

        )


    try:

        sources = search_exa(
            query=q.strip()
        )


        return {

            "query": q,

            "provider": "Exa",

            "results":
                clean_sources(
                    sources
                ),

        }


    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(error),

        )


# ============================================================
# CREATE CONVERSATION
# ============================================================

@app.post(
    "/conversations"
)
def create_new_conversation_endpoint(

    request: ConversationRequest,

    db: Session = Depends(
        get_db
    ),

):


    conversation = create_conversation(

        db,

        request.title
        or "New Conversation",

    )


    return {

        "id":
            conversation.id,

        "title":
            conversation.title,

        "created_at":
            conversation.created_at,

        "updated_at":
            conversation.updated_at,

    }


# ============================================================
# GET CONVERSATIONS
# ============================================================

@app.get(
    "/conversations"
)
def get_conversations(

    db: Session = Depends(
        get_db
    ),

):


    conversations = (

        db.query(
            Conversation
        )

        .order_by(
            Conversation.updated_at.desc()
        )

        .all()

    )


    return [

        {

            "id":
                conversation.id,

            "title":
                conversation.title,

            "created_at":
                conversation.created_at,

            "updated_at":
                conversation.updated_at,

        }

        for conversation
        in conversations

    ]


# ============================================================
# GET CONVERSATION
# ============================================================

@app.get(
    "/conversations/{conversation_id}"
)
def get_conversation(

    conversation_id: int,

    db: Session = Depends(
        get_db
    ),

):


    conversation = (

        db.query(
            Conversation
        )

        .filter(
            Conversation.id
            == conversation_id
        )

        .first()

    )


    if not conversation:

        raise HTTPException(

            status_code=404,

            detail=(
                "Conversation not found."
            ),

        )


    messages = (

        db.query(
            Message
        )

        .filter(
            Message.conversation_id
            == conversation_id
        )

        .order_by(
            Message.created_at.asc()
        )

        .all()

    )


    return {

        "id":
            conversation.id,

        "title":
            conversation.title,

        "created_at":
            conversation.created_at,

        "updated_at":
            conversation.updated_at,

        "messages": [

            {

                "id":
                    message.id,

                "role":
                    message.role,

                "content":
                    message.content,

                "created_at":
                    message.created_at,

                "sources": [],

                "web_search_used":
                    False,

                "calculator_used":
                    False,

            }

            for message
            in messages

        ],

    }


# ============================================================
# UPDATE CONVERSATION
# ============================================================

@app.put(
    "/conversations/{conversation_id}"
)
def update_conversation(

    conversation_id: int,

    request:
        UpdateConversationRequest,

    db: Session = Depends(
        get_db
    ),

):


    conversation = (

        db.query(
            Conversation
        )

        .filter(
            Conversation.id
            == conversation_id
        )

        .first()

    )


    if not conversation:

        raise HTTPException(

            status_code=404,

            detail=(
                "Conversation not found."
            ),

        )


    conversation.title = (
        request.title.strip()
    )


    conversation.updated_at = (
        datetime.now(timezone.utc)
    )


    commit_database(
        db
    )


    db.refresh(
        conversation
    )


    return {

        "id":
            conversation.id,

        "title":
            conversation.title,

        "created_at":
            conversation.created_at,

        "updated_at":
            conversation.updated_at,

    }


# ============================================================
# DELETE CONVERSATION
# ============================================================

@app.delete(
    "/conversations/{conversation_id}"
)
def delete_conversation(

    conversation_id: int,

    db: Session = Depends(
        get_db
    ),

):


    conversation = (

        db.query(
            Conversation
        )

        .filter(
            Conversation.id
            == conversation_id
        )

        .first()

    )


    if not conversation:

        raise HTTPException(

            status_code=404,

            detail=(
                "Conversation not found."
            ),

        )


    db.delete(
        conversation
    )


    commit_database(
        db
    )


    return {

        "success": True,

        "message":
            "Conversation deleted.",

    }


# ============================================================
# NORMAL CHAT
# ============================================================

@app.post(
    "/chat"
)
def chat(

    request: ChatRequest,

    db: Session = Depends(
        get_db
    ),

):


    user_message = (
        request.message.strip()
    )


    if not user_message:

        raise HTTPException(

            status_code=400,

            detail=(
                "Please enter a message."
            ),

        )


    try:

        route = route_message(user_message)

        user_key = (
            request.user_key.strip()
            or DEFAULT_USER_KEY
        )

        memory_result = retrieve_memory_context(
            db=db,
            query=user_message,
            user_key=user_key,
            limit=5,
        )

        memory_context = memory_result["context"]

        print()
        print("=" * 60)
        print("🧠 IGNYX AI ROUTER")
        print("Intent:", route["intent"])
        print("Confidence:", route["confidence"])
        print("Reason:", route["reason"])
        print("Tools:", ", ".join(route["tools"]) or "none")
        print("=" * 60)
        print()



        conversation = (

            get_or_create_conversation(

                db,

                request.conversation_id,

                user_message,

            )

        )


        save_message(

            db,

            conversation.id,

            "user",

            user_message,

        )


        calculation = (

            calculate_from_message(
                user_message
            )

        )


        raw_sources = []


        if calculation:


            answer = (

                f"The result of "

                f"`{calculation['expression']}` "

                f"is "

                f"**{calculation['result']}**."

            )


        else:


            history = (

                get_conversation_history(

                    db,

                    conversation.id,

                )

            )


            if history:

                history = history[:-1]


            manual_web_search = bool(
                request.web_search
            )


            # The AI router controls automatic web-search selection.
            # The frontend may also explicitly enable web search.
            # Keyword-based auto-search is intentionally disabled here
            # so normal conversation and coding requests do not trigger Exa.
            use_web_search = (
                manual_web_search
                or route["intent"] == "web_search"
            )


            web_context = ""


            if use_web_search:


                try:

                    raw_sources = (

                        search_exa(
                            user_message
                        )

                    )


                    web_context = (

                        build_web_context(
                            raw_sources
                        )

                    )


                except Exception as search_error:

                    print(
                        "EXA WARNING:",
                        str(search_error)
                    )


            prompt = build_prompt(

                user_message,

                history,

                web_context,

                route,

                memory_context,

            )


            answer = (
                generate_ai_response(
                    prompt
                )
            )


        save_message(

            db,

            conversation.id,

            "assistant",

            answer,

        )

        saved_memories = save_extracted_memories(
            db=db,
            message=user_message,
            user_key=user_key,
        )


        return {

            "response":
                answer,

            "conversation_id":
                conversation.id,

            "web_search_used":

                use_web_search

                if not calculation
                else False,

            "calculator_used":

                calculation is not None,

            "intent":

                route["intent"],

            "route_confidence":

                route["confidence"],

            "tools_used":

                route["tools"],

            "memory_used": memory_result["count"] > 0,

            "memories_saved": saved_memories,

            "memory_count": memory_result["count"],

            "sources":

                clean_sources(
                    raw_sources
                ),

        }


    except GeminiQuotaError as error:

        print(
            "CHAT GEMINI QUOTA:",
            str(error)
        )

        return JSONResponse(
            status_code=200,
            content={
                "error": True,
                "type": "ai_quota_exceeded",
                "message": str(error),
            },
        )


    except GeminiBusyError as error:

        print(
            "CHAT AI BUSY:",
            str(error)
        )

        return JSONResponse(
            status_code=200,
            content={
                "error": True,
                "type": "ai_busy",
                "message": str(error),
            },
        )


    except Exception as error:

        print(
            "CHAT ERROR:",
            str(error)
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "type": "server_error",
                "message": (
                    "IGNYX could not complete the request. "
                    "Please try again."
                ),
            },
        )
@app.post(
    "/chat/stream"
)
def chat_stream(

    request: ChatRequest,

):


    return StreamingResponse(

        stream_response(
            request
        ),

        media_type=(
            "text/event-stream"
        ),

        headers={

            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",

        },

    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print("Starting IGNYX AI on http://127.0.0.1:8000")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
