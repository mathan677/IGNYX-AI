# ============================================================
# IGNYX AI BACKEND
# Complete FastAPI + Gemini + Database Backend
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import ast
import json
import operator
import os
import re

from datetime import datetime

from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
)


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

from google.genai import (
    types,
)


from database import (
    Base,
    SessionLocal,
    engine,
)


from models import (
    Conversation,
    Message,
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


# ============================================================
# GEMINI MODEL
# ============================================================

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# APPLICATION SETTINGS
# ============================================================

MAX_HISTORY_MESSAGES = 12

MAX_HISTORY_MESSAGE_LENGTH = 5000

MAX_OUTPUT_TOKENS = 8192

MAX_MESSAGE_LENGTH = 10000


# ============================================================
# FRONTEND URLS
# ============================================================

FRONTEND_ORIGINS = [

    "http://localhost:3000",

    "http://127.0.0.1:3000",

]


# ============================================================
# VALIDATE API KEY
# ============================================================

if not GEMINI_API_KEY:

    raise RuntimeError(

        "GEMINI_API_KEY is missing. "
        "Please add it to your backend .env file."

    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(

    api_key=GEMINI_API_KEY

)


# ============================================================
# DATABASE INITIALIZATION
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
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title="IGNYX AI API",

    description=(
        "IGNYX AI Assistant Backend "
        "powered by Google Gemini"
    ),

    version="3.0.0",

)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=FRONTEND_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatRequest(

    BaseModel

):

    message: str = Field(

        ...,

        min_length=1,

        max_length=MAX_MESSAGE_LENGTH,

    )


    conversation_id: Optional[int] = None


    web_search: Optional[bool] = None


# ============================================================
# CONVERSATION REQUEST
# ============================================================

class ConversationRequest(

    BaseModel

):

    title: Optional[str] = Field(

        default="New conversation",

        max_length=200,

    )


# ============================================================
# IGNYX SYSTEM INSTRUCTIONS
# ============================================================

IGNYX_INSTRUCTIONS = """

You are IGNYX, an intelligent AI assistant.

Your name is IGNYX.


Your goals:

- Give helpful, accurate and clear answers.
- Explain concepts in an easy-to-understand way.
- Be professional and friendly.
- Be conversational.
- Use Markdown when useful.
- Use headings when useful.
- Use bullet points when useful.
- Use tables when useful.
- Use code blocks for programming examples.
- Keep code syntactically correct.
- Be concise for simple questions.
- Be detailed for educational questions.
- Be detailed for technical questions.
- Do not invent facts.
- Do not invent sources.
- If uncertain, clearly say so.


You can help with:

- Artificial Intelligence
- Machine Learning
- Deep Learning
- Data Science
- Data Analysis
- Python
- SQL
- Programming
- Web Development
- Generative AI
- Large Language Models
- RAG
- AI Agents
- Mathematics
- Career Guidance
- General Knowledge


When explaining programming:

- Explain the code clearly.
- Use examples when useful.
- Keep examples correct.
- Explain important concepts.


When calculator results are provided:

- Use the calculator result accurately.
- Do not contradict the calculator result.


When web search is available:

- Use current information carefully.
- Use the search results.
- Do not invent sources.


Always be helpful, professional and conversational.

"""


# ============================================================
# SAFE CALCULATOR
# ============================================================

SAFE_OPERATORS = {

    ast.Add:
        operator.add,


    ast.Sub:
        operator.sub,


    ast.Mult:
        operator.mul,


    ast.Div:
        operator.truediv,


    ast.FloorDiv:
        operator.floordiv,


    ast.Mod:
        operator.mod,


    ast.Pow:
        operator.pow,


    ast.USub:
        operator.neg,


    ast.UAdd:
        operator.pos,

}


# ============================================================
# SAFE CALCULATOR FUNCTION
# ============================================================

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


    def evaluate(

        node,

    ):


        # ====================================================
        # NUMBER
        # ====================================================

        if isinstance(

            node,

            ast.Constant,

        ):


            if isinstance(

                node.value,

                (
                    int,
                    float,
                ),

            ):

                return node.value


            raise ValueError(

                "Invalid number."

            )


        # ====================================================
        # BINARY OPERATION
        # ====================================================

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


            # =================================================
            # DIVISION BY ZERO
            # =================================================

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


            # =================================================
            # LIMIT EXPONENT
            # =================================================

            if isinstance(

                node.op,

                ast.Pow,

            ):


                if abs(right) > 100:

                    raise ValueError(

                        "Exponent is too large."

                    )


            return SAFE_OPERATORS[

                operator_type

            ](

                left,

                right,

            )


        # ====================================================
        # UNARY OPERATION
        # ====================================================

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

) -> Optional[Dict[str, Any]]:


    message = message.strip()


    cleaned = re.sub(

        r"^(calculate|solve|compute|what is)\s*",

        "",

        message.lower(),

    ).strip()


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

        r"[0-9\s\+\-\*\/\.\(\)\%\:]+"

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

            "expression":
                cleaned,

            "result":
                result,

        }


    except Exception:

        return None


# ============================================================
# WEB SEARCH DETECTION
# ============================================================

CURRENT_KEYWORDS = [

    "latest",

    "today",

    "current",

    "currently",

    "news",

    "recent",

    "recently",

    "breaking",

    "live",

    "updated",

    "update",

    "yesterday",

    "tomorrow",

    "weather",

    "temperature",

    "forecast",

    "stock",

    "stocks",

    "market",

    "price",

    "prices",

    "score",

    "scores",

    "who won",

    "election",

    "release date",

]


# ============================================================
# SHOULD USE WEB SEARCH
# ============================================================

def should_use_web_search(

    message: str,

) -> bool:


    message_lower = message.lower()


    return any(

        keyword in message_lower

        for keyword

        in CURRENT_KEYWORDS

    )


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

def build_config(

    use_web_search: bool = False,

):


    tools = None


    # ========================================================
    # GOOGLE SEARCH
    # ========================================================

    if use_web_search:


        tools = [

            types.Tool(

                google_search=(

                    types.GoogleSearch()

                )

            )

        ]


    return types.GenerateContentConfig(

        system_instruction=(

            IGNYX_INSTRUCTIONS

        ),

        tools=tools,

        temperature=0.7,

        max_output_tokens=(

            MAX_OUTPUT_TOKENS

        ),

    )


# ============================================================
# DATABASE COMMIT
# ============================================================

def commit_db(

    db: Session,

):


    try:

        db.commit()


    except Exception:


        db.rollback()


        raise


# ============================================================
# CREATE NEW CONVERSATION
# ============================================================

def create_new_conversation(

    db: Session,

    first_message: str,

) -> Conversation:


    title = first_message.strip()


    if len(title) > 60:


        title = (

            title[:60].rstrip()

            + "..."

        )


    if not title:

        title = "New conversation"


    conversation = Conversation(

        title=title

    )


    db.add(

        conversation

    )


    commit_db(

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

) -> Conversation:


    # ========================================================
    # EXISTING CONVERSATION
    # ========================================================

    if conversation_id is not None:


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


        if conversation is None:


            raise HTTPException(

                status_code=404,

                detail=(

                    "Conversation not found."

                ),

            )


        return conversation


    # ========================================================
    # NEW CONVERSATION
    # ========================================================

    return create_new_conversation(

        db=db,

        first_message=first_message,

    )


# ============================================================
# UPDATE CONVERSATION TIME
# ============================================================

def update_conversation_timestamp(

    db: Session,

    conversation_id: int,

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


    if conversation:


        try:


            conversation.updated_at = (

                datetime.utcnow()

            )


        except Exception:

            pass


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(

    db: Session,

    conversation_id: int,

    role: str,

    content: str,

) -> Message:


    message = Message(

        conversation_id=conversation_id,

        role=role,

        content=content,

    )


    db.add(

        message

    )


    update_conversation_timestamp(

        db,

        conversation_id,

    )


    commit_db(

        db

    )


    db.refresh(

        message

    )


    return message


# ============================================================
# GET CONVERSATION HISTORY
# ============================================================

def get_conversation_history(

    db: Session,

    conversation_id: int,

    limit: int = MAX_HISTORY_MESSAGES,

) -> List[Dict[str, str]]:


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


    history = []


    for message in messages[-limit:]:


        content = (

            message.content

            or ""

        )


        if (

            len(content)

            > MAX_HISTORY_MESSAGE_LENGTH

        ):


            content = content[

                -MAX_HISTORY_MESSAGE_LENGTH:

            ]


        history.append(

            {

                "role":
                    message.role,

                "content":
                    content,

            }

        )


    return history


# ============================================================
# BUILD AI PROMPT
# ============================================================

def build_prompt(

    user_message: str,

    calculator_result: Optional[
        Dict[str, Any]
    ] = None,

    conversation_history: Optional[
        List[Dict[str, str]]
    ] = None,

) -> str:


    parts = []


    # ========================================================
    # CONVERSATION HISTORY
    # ========================================================

    if conversation_history:


        parts.append(

            "Conversation history:"

        )


        for item in conversation_history:


            role = item.get(

                "role",

                "user",

            )


            content = item.get(

                "content",

                "",

            )


            parts.append(

                f"{role.upper()}: {content}"

            )


    # ========================================================
    # CALCULATOR
    # ========================================================

    if calculator_result is not None:


        parts.append(

            "Calculator information:"

        )


        parts.append(

            "Expression: "

            + str(

                calculator_result[
                    "expression"
                ]

            )

        )


        parts.append(

            "Result: "

            + str(

                calculator_result[
                    "result"
                ]

            )

        )


        parts.append(

            "Use this calculator result "
            "accurately."

        )


    # ========================================================
    # USER QUESTION
    # ========================================================

    parts.append(

        "Current user question:"

    )


    parts.append(

        user_message

    )


    return "\n\n".join(

        parts

    )


# ============================================================
# MERGE SOURCES
# ============================================================

def merge_sources(

    sources: List[
        Dict[str, str]
    ],

) -> List[
    Dict[str, str]
]:


    unique_sources = []


    seen_urls = set()


    for source in sources:


        url = (

            source.get(

                "url"

            )

            or ""

        )


        if not url:

            continue


        if url in seen_urls:

            continue


        seen_urls.add(

            url

        )


        unique_sources.append(

            {

                "title": (

                    source.get(
                        "title"
                    )

                    or url

                ),

                "url":
                    url,

            }

        )


    return unique_sources


# ============================================================
# EXTRACT GOOGLE SEARCH SOURCES
# ============================================================

def extract_sources(

    response: Any,

) -> List[
    Dict[str, str]
]:


    sources = []


    if response is None:

        return sources


    try:


        candidates = getattr(

            response,

            "candidates",

            [],

        ) or []


        for candidate in candidates:


            grounding_metadata = getattr(

                candidate,

                "grounding_metadata",

                None,

            )


            if not grounding_metadata:

                continue


            grounding_chunks = getattr(

                grounding_metadata,

                "grounding_chunks",

                [],

            ) or []


            for chunk in grounding_chunks:


                web = getattr(

                    chunk,

                    "web",

                    None,

                )


                if not web:

                    continue


                title = getattr(

                    web,

                    "title",

                    "",

                ) or ""


                uri = getattr(

                    web,

                    "uri",

                    "",

                ) or ""


                if uri:


                    sources.append(

                        {

                            "title": (

                                title

                                or uri

                            ),

                            "url":
                                uri,

                        }

                    )


    except Exception as error:


        print(

            "Source extraction error:",

            str(error),

        )


    return merge_sources(

        sources

    )


# ============================================================
# SERVER SENT EVENT
# ============================================================

def sse_event(

    data: Dict[str, Any],

) -> str:


    return (

        "data: "

        + json.dumps(

            data,

            ensure_ascii=False,

            default=str,

        )

        + "\n\n"

    )


# ============================================================
# ROOT API
# ============================================================

@app.get("/")
def root():


    return {

        "message":
            "IGNYX AI API is running",

        "status":
            "online",

        "model":
            MODEL_NAME,

        "version":
            "3.0.0",

    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():


    return {

        "status":
            "healthy",

        "service":
            "IGNYX AI",

        "provider":
            "Google Gemini",

        "model":
            MODEL_NAME,

        "database":
            "connected",

        "features": {

            "chat":
                True,

            "streaming":
                True,

            "conversations":
                True,

            "web_search":
                True,

            "calculator":
                True,

            "sources":
                True,

        },

    }


# ============================================================
# CREATE CONVERSATION
# ============================================================

@app.post("/conversations")
def create_conversation_api(

    request: ConversationRequest,

    db: Session = Depends(
        get_db
    ),

):


    title = (

        request.title

        or "New conversation"

    ).strip()


    conversation = Conversation(

        title=title

    )


    db.add(

        conversation

    )


    commit_db(

        db

    )


    db.refresh(

        conversation

    )


    return {

        "success":
            True,

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
# GET ALL CONVERSATIONS
# ============================================================

@app.get("/conversations")
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
# GET SINGLE CONVERSATION
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


    if conversation is None:


        raise HTTPException(

            status_code=404,

            detail="Conversation not found.",

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
# GET CONVERSATION MESSAGES
# ============================================================

@app.get(
    "/conversations/{conversation_id}/messages"
)
def get_conversation_messages(

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


    if conversation is None:


        raise HTTPException(

            status_code=404,

            detail="Conversation not found.",

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


    return [

        {

            "id":
                message.id,

            "conversation_id":
                message.conversation_id,

            "role":
                message.role,

            "content":
                message.content,

            "created_at":
                message.created_at,

        }

        for message

        in messages

    ]


# ============================================================
# RENAME CONVERSATION
# ============================================================

@app.put(
    "/conversations/{conversation_id}"
)
def rename_conversation(

    conversation_id: int,

    request: ConversationRequest,

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


    if conversation is None:


        raise HTTPException(

            status_code=404,

            detail="Conversation not found.",

        )


    title = (

        request.title

        or "New conversation"

    ).strip()


    if not title:

        title = "New conversation"


    conversation.title = title


    try:

        conversation.updated_at = (

            datetime.utcnow()

        )

    except Exception:

        pass


    commit_db(

        db

    )


    db.refresh(

        conversation

    )


    return {

        "success":
            True,

        "id":
            conversation.id,

        "title":
            conversation.title,

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


    if conversation is None:


        raise HTTPException(

            status_code=404,

            detail="Conversation not found.",

        )


    # ========================================================
    # DELETE MESSAGES
    # ========================================================

    db.query(

        Message

    ).filter(

        Message.conversation_id

        == conversation_id

    ).delete(

        synchronize_session=False

    )


    # ========================================================
    # DELETE CONVERSATION
    # ========================================================

    db.delete(

        conversation

    )


    commit_db(

        db

    )


    return {

        "success":
            True,

        "message":
            "Conversation deleted.",

    }


# ============================================================
# NORMAL CHAT API
# ============================================================

@app.post("/chat")
def chat(

    request: ChatRequest,

    db: Session = Depends(
        get_db
    ),

):


    conversation_id = None


    try:


        # ====================================================
        # CLEAN MESSAGE
        # ====================================================

        user_message = (

            request.message.strip()

        )


        if not user_message:


            return {

                "response":
                    "Please enter a message.",

                "error":
                    False,

                "conversation_id":
                    request.conversation_id,

                "web_search_used":
                    False,

                "calculator_used":
                    False,

                "calculator_result":
                    None,

                "sources":
                    [],

            }


        # ====================================================
        # CONVERSATION
        # ====================================================

        conversation = (

            get_or_create_conversation(

                db=db,

                conversation_id=(
                    request.conversation_id
                ),

                first_message=(
                    user_message
                ),

            )

        )


        conversation_id = (

            conversation.id

        )


        # ====================================================
        # GET HISTORY
        # ====================================================

        history = (

            get_conversation_history(

                db=db,

                conversation_id=(
                    conversation_id
                ),

            )

        )


        # ====================================================
        # SAVE USER MESSAGE
        # ====================================================

        save_message(

            db=db,

            conversation_id=(
                conversation_id
            ),

            role="user",

            content=user_message,

        )


        # ====================================================
        # CALCULATOR
        # ====================================================

        calculator_result = (

            calculate_from_message(

                user_message

            )

        )


        calculator_used = (

            calculator_result

            is not None

        )


        # ====================================================
        # WEB SEARCH
        # ====================================================

        if request.web_search is None:


            use_web_search = (

                should_use_web_search(

                    user_message

                )

            )


        else:


            use_web_search = (

                request.web_search

            )


        # ====================================================
        # BUILD PROMPT
        # ====================================================

        prompt = build_prompt(

            user_message=user_message,

            calculator_result=(
                calculator_result
            ),

            conversation_history=(
                history
            ),

        )


        # ====================================================
        # GEMINI RESPONSE
        # ====================================================

        response = (

            client.models.generate_content(

                model=MODEL_NAME,

                contents=prompt,

                config=build_config(

                    use_web_search

                ),

            )

        )


        final_text = (

            getattr(

                response,

                "text",

                "",

            )

            or ""

        ).strip()


        # ====================================================
        # EMPTY RESPONSE
        # ====================================================

        if not final_text:


            final_text = (

                "I could not generate "
                "a response. Please try again."

            )


        # ====================================================
        # SOURCES
        # ====================================================

        sources = extract_sources(

            response

        )


        # ====================================================
        # SAVE ASSISTANT RESPONSE
        # ====================================================

        save_message(

            db=db,

            conversation_id=(
                conversation_id
            ),

            role="assistant",

            content=final_text,

        )


        # ====================================================
        # RETURN RESPONSE
        # ====================================================

        return {

            "response":
                final_text,

            "error":
                False,

            "conversation_id":
                conversation_id,

            "web_search_used":
                use_web_search,

            "calculator_used":
                calculator_used,

            "calculator_result":
                calculator_result,

            "sources":
                sources,

        }


    except HTTPException:

        raise


    except Exception as error:


        error_details = str(

            error

        )


        print(

            "\n"
            + "=" * 60

        )


        print(

            "CHAT API ERROR"

        )


        print(

            error_details

        )


        print(

            "=" * 60
            + "\n"

        )


        return {

            "response":
                "",

            "error":
                True,

            "conversation_id":
                conversation_id,

            "web_search_used":
                False,

            "calculator_used":
                False,

            "calculator_result":
                None,

            "sources":
                [],

            "message":
                error_details,

        }


# ============================================================
# STREAMING CHAT API
# ============================================================

@app.post("/chat/stream")
def chat_stream(

    request: ChatRequest,

    db: Session = Depends(
        get_db
    ),

):


    # ========================================================
    # CLEAN MESSAGE
    # ========================================================

    user_message = (

        request.message.strip()

    )


    # ========================================================
    # EMPTY MESSAGE
    # ========================================================

    if not user_message:


        def empty_generator():


            yield sse_event(

                {

                    "type":
                        "error",

                    "message":
                        "Please enter a message.",

                }

            )


        return StreamingResponse(

            empty_generator(),

            media_type="text/event-stream",

        )


    # ========================================================
    # CONVERSATION
    # ========================================================

    conversation = (

        get_or_create_conversation(

            db=db,

            conversation_id=(
                request.conversation_id
            ),

            first_message=(
                user_message
            ),

        )

    )


    conversation_id = (

        conversation.id

    )


    # ========================================================
    # HISTORY
    # ========================================================

    history = (

        get_conversation_history(

            db=db,

            conversation_id=(
                conversation_id
            ),

        )

    )


    # ========================================================
    # SAVE USER MESSAGE
    # ========================================================

    save_message(

        db=db,

        conversation_id=(
            conversation_id
        ),

        role="user",

        content=user_message,

    )


    # ========================================================
    # CALCULATOR
    # ========================================================

    calculator_result = (

        calculate_from_message(

            user_message

        )

    )


    calculator_used = (

        calculator_result

        is not None

    )


    # ========================================================
    # WEB SEARCH
    # ========================================================

    if request.web_search is None:


        use_web_search = (

            should_use_web_search(

                user_message

            )

        )


    else:


        use_web_search = (

            request.web_search

        )


    # ========================================================
    # BUILD PROMPT
    # ========================================================

    prompt = build_prompt(

        user_message=user_message,

        calculator_result=(
            calculator_result
        ),

        conversation_history=(
            history
        ),

    )


    # ========================================================
    # STREAM GENERATOR
    # ========================================================

    def generate() -> Generator[

        str,

        None,

        None,

    ]:


        accumulated_text = ""


        all_sources = []


        try:


            # =================================================
            # GEMINI STREAM
            # =================================================

            stream = (

                client.models.generate_content_stream(

                    model=MODEL_NAME,

                    contents=prompt,

                    config=build_config(

                        use_web_search

                    ),

                )

            )


            # =================================================
            # PROCESS STREAM
            # =================================================

            for chunk in stream:


                # =============================================
                # GET SOURCES
                # =============================================

                chunk_sources = (

                    extract_sources(

                        chunk

                    )

                )


                if chunk_sources:


                    all_sources.extend(

                        chunk_sources

                    )


                # =============================================
                # GET TEXT
                # =============================================

                chunk_text = (

                    getattr(

                        chunk,

                        "text",

                        "",

                    )

                    or ""

                )


                if not chunk_text:

                    continue


                accumulated_text += (

                    chunk_text

                )


                # =============================================
                # SEND DELTA
                # =============================================

                yield sse_event(

                    {

                        "type":
                            "delta",

                        "text":
                            chunk_text,

                    }

                )


            # =================================================
            # EMPTY RESPONSE
            # =================================================

            if not accumulated_text.strip():


                accumulated_text = (

                    "Gemini returned an "
                    "empty response."

                )


                yield sse_event(

                    {

                        "type":
                            "delta",

                        "text":
                            accumulated_text,

                    }

                )


            # =================================================
            # FINAL SOURCES
            # =================================================

            all_sources = merge_sources(

                all_sources

            )


            # =================================================
            # SAVE ASSISTANT RESPONSE
            # =================================================

            save_message(

                db=db,

                conversation_id=(
                    conversation_id
                ),

                role="assistant",

                content=(
                    accumulated_text
                ),

            )


            # =================================================
            # SEND DONE EVENT
            # =================================================

            yield sse_event(

                {

                    "type":
                        "done",

                    "conversation_id":
                        conversation_id,

                    "web_search_used":
                        use_web_search,

                    "calculator_used":
                        calculator_used,

                    "calculator_result":
                        calculator_result,

                    "sources":
                        all_sources,

                }

            )


        # ====================================================
        # ERROR
        # ====================================================

        except Exception as error:


            error_details = str(

                error

            )


            print(

                "\n"
                + "=" * 60

            )


            print(

                "GEMINI STREAM ERROR"

            )


            print(

                error_details

            )


            print(

                "=" * 60
                + "\n"

            )


            yield sse_event(

                {

                    "type":
                        "error",

                    "message":
                        error_details,

                    "conversation_id":
                        conversation_id,

                }

            )


    # ========================================================
    # RETURN STREAMING RESPONSE
    # ========================================================

    return StreamingResponse(

        generate(),

        media_type="text/event-stream",

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
# APPLICATION STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():


    print(

        "\n"

        + "=" * 60

    )


    print(

        "IGNYX AI BACKEND"

    )


    print(

        "=" * 60

    )


    print(

        "API Docs: "
        "http://127.0.0.1:8000/docs"

    )


    print(

        "Gemini Model:",

        MODEL_NAME,

    )


    print(

        "Gemini Ready:",

        True,

    )


    print(

        "Web Search:",

        "Enabled",

    )


    print(

        "Calculator:",

        "Enabled",

    )


    print(

        "Streaming:",

        "Enabled",

    )


    print(

        "Database:",

        "Enabled",

    )


    print(

        "=" * 60

        + "\n"

    )


# ============================================================
# APPLICATION SHUTDOWN
# ============================================================

@app.on_event("shutdown")
def shutdown_event():


    print(

        "\nIGNYX AI backend stopped.\n"

    )