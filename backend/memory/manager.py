import json
import os
import re
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from sqlalchemy.orm import Session

from memory.models import Memory


load_dotenv()


DEFAULT_USER_KEY = "default_user"

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768

# =========================================================
# MEMORY QUALITY LIMITS
# =========================================================

MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 150

MIN_VALUE_LENGTH = 2
MAX_VALUE_LENGTH = 1000

MAX_CATEGORY_LENGTH = 50

# Values that should never become long-term memories.
BLOCKED_VALUES = {
    "test",
    "testing",
    "hello",
    "hi",
    "ok",
    "okay",
    "none",
    "null",
    "unknown",
    "n/a",
    "na",
    "placeholder",
}


# =========================================================
# GEMINI EMBEDDING CLIENT
# =========================================================

_embedding_client = None


def _get_embedding_client():
    global _embedding_client

    if _embedding_client is not None:
        return _embedding_client

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    try:
        _embedding_client = genai.Client(
            api_key=api_key,
        )

        return _embedding_client

    except Exception as exc:
        print(
            f"[MEMORY] Could not initialize embedding client: {exc}"
        )

        return None


# =========================================================
# MEMORY QUALITY HELPERS
# =========================================================

def _clean_whitespace(
    value: str,
) -> str:
    return " ".join(
        value.strip().split()
    )


def _validate_memory_text(
    key: str,
    value: str,
) -> None:
    """
    Validate memory key/value before persistence.

    Raises ValueError when the memory is clearly invalid
    or unsuitable for long-term storage.
    """

    if len(key) < MIN_KEY_LENGTH:
        raise ValueError(
            "Memory key is too short."
        )

    if len(key) > MAX_KEY_LENGTH:
        raise ValueError(
            "Memory key is too long."
        )

    if len(value) < MIN_VALUE_LENGTH:
        raise ValueError(
            "Memory value is too short."
        )

    if len(value) > MAX_VALUE_LENGTH:
        raise ValueError(
            "Memory value is too long."
        )

    normalized_value = value.lower().strip()

    if normalized_value in BLOCKED_VALUES:
        raise ValueError(
            "Memory value is not meaningful enough to store."
        )

    # Reject values that are only punctuation/symbols.
    if not re.search(
        r"[A-Za-z0-9]",
        value,
    ):
        raise ValueError(
            "Memory value must contain meaningful text."
        )


def _normalize_memory_key(
    key: str,
) -> str:
    """
    Normalize memory keys so equivalent keys don't create
    accidental duplicates.
    """

    clean_key = _clean_whitespace(
        key
    )

    clean_key = clean_key.lower()

    clean_key = re.sub(
        r"\s+",
        "_",
        clean_key,
    )

    clean_key = re.sub(
        r"[^a-z0-9_:-]",
        "",
        clean_key,
    )

    return clean_key[:MAX_KEY_LENGTH]


def _normalize_category(
    category: str,
) -> str:
    clean_category = _clean_whitespace(
        category
    )

    if not clean_category:
        return "general"

    return clean_category[:MAX_CATEGORY_LENGTH]


def _normalize_importance(
    importance: float,
) -> float:
    try:
        clean_importance = float(
            importance
        )

    except (
        TypeError,
        ValueError,
    ):
        clean_importance = 0.5

    return max(
        0.0,
        min(
            clean_importance,
            1.0,
        ),
    )


def _build_memory_text(
    key: str,
    value: str,
    category: str,
) -> str:
    return (
        f"category: {category}; "
        f"key: {key}; "
        f"value: {value}"
    )


# =========================================================
# EMBEDDING GENERATION
# =========================================================

def _generate_embedding(
    text: str,
) -> Optional[List[float]]:
    """
    Generate a Gemini semantic embedding.

    Returns None when embeddings are unavailable.
    """

    clean_text = _clean_whitespace(
        text
    )

    if not clean_text:
        return None

    client = _get_embedding_client()

    if client is None:
        return None

    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=clean_text,
            config={
                "output_dimensionality": EMBEDDING_DIMENSION,
            },
        )

        if not result or not result.embeddings:
            return None

        values = result.embeddings[0].values

        if not values:
            return None

        return [
            float(value)
            for value in values
        ]

    except Exception as exc:
        # Memory operations must remain functional even
        # when Gemini embedding generation temporarily fails.
        print(
            f"[MEMORY] Embedding generation failed: {exc}"
        )

        return None


def _embedding_to_json(
    embedding: Optional[List[float]],
) -> Optional[str]:
    if not embedding:
        return None

    try:
        return json.dumps(
            embedding,
            separators=(",", ":"),
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


# =========================================================
# CREATE / UPSERT MEMORY
# =========================================================

def create_memory(
    db: Session,
    key: str,
    value: str,
    category: str = "general",
    importance: float = 0.5,
    user_key: str = DEFAULT_USER_KEY,
) -> Memory:
    """
    Create a new memory or update an existing memory.

    Quality controls:
        - normalized key
        - normalized category
        - normalized whitespace
        - value length protection
        - invalid/placeholder value rejection
        - importance clamped to 0..1
        - semantic embedding generation
        - exact-key deduplication
    """

    clean_key = _normalize_memory_key(
        key
    )

    clean_value = _clean_whitespace(
        value
    )

    clean_category = _normalize_category(
        category
    )

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    if not clean_key:
        raise ValueError(
            "Memory key is required."
        )

    if not clean_value:
        raise ValueError(
            "Memory value is required."
        )

    _validate_memory_text(
        key=clean_key,
        value=clean_value,
    )

    clean_importance = _normalize_importance(
        importance
    )

    # =====================================================
    # FIND EXISTING MEMORY
    # =====================================================

    existing = (
        db.query(Memory)
        .filter(
            Memory.user_key == clean_user_key,
            Memory.key == clean_key,
        )
        .first()
    )

    # =====================================================
    # UPDATE EXISTING MEMORY
    # =====================================================

    if existing:

        content_changed = (
            existing.value != clean_value
            or existing.category != clean_category
        )

        existing.value = clean_value
        existing.category = clean_category
        existing.importance = clean_importance

        # Don't regenerate an embedding when the semantic
        # content hasn't changed.
        if content_changed:

            memory_text = _build_memory_text(
                key=clean_key,
                value=clean_value,
                category=clean_category,
            )

            embedding = _generate_embedding(
                memory_text
            )

            embedding_json = _embedding_to_json(
                embedding
            )

            if embedding_json is not None:
                existing.embedding = embedding_json

        # Existing memory had no embedding.
        elif not existing.embedding:

            memory_text = _build_memory_text(
                key=clean_key,
                value=clean_value,
                category=clean_category,
            )

            embedding = _generate_embedding(
                memory_text
            )

            embedding_json = _embedding_to_json(
                embedding
            )

            if embedding_json is not None:
                existing.embedding = embedding_json

        db.commit()
        db.refresh(existing)

        return existing

    # =====================================================
    # CREATE NEW MEMORY
    # =====================================================

    memory_text = _build_memory_text(
        key=clean_key,
        value=clean_value,
        category=clean_category,
    )

    embedding = _generate_embedding(
        memory_text
    )

    embedding_json = _embedding_to_json(
        embedding
    )

    memory = Memory(
        user_key=clean_user_key,
        category=clean_category,
        key=clean_key,
        value=clean_value,
        importance=clean_importance,
        embedding=embedding_json,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


# =========================================================
# GET ALL MEMORIES
# =========================================================

def get_all_memories(
    db: Session,
    user_key: str = DEFAULT_USER_KEY,
) -> List[Memory]:

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    return (
        db.query(Memory)
        .filter(
            Memory.user_key == clean_user_key
        )
        .order_by(
            Memory.importance.desc(),
            Memory.updated_at.desc(),
        )
        .all()
    )


# =========================================================
# GET MEMORY BY ID
# =========================================================

def get_memory_by_id(
    db: Session,
    memory_id: int,
    user_key: str = DEFAULT_USER_KEY,
) -> Optional[Memory]:

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    return (
        db.query(Memory)
        .filter(
            Memory.id == memory_id,
            Memory.user_key == clean_user_key,
        )
        .first()
    )


# =========================================================
# GET MEMORY BY KEY
# =========================================================

def get_memory_by_key(
    db: Session,
    key: str,
    user_key: str = DEFAULT_USER_KEY,
) -> Optional[Memory]:

    clean_key = _normalize_memory_key(
        key
    )

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    if not clean_key:
        return None

    return (
        db.query(Memory)
        .filter(
            Memory.key == clean_key,
            Memory.user_key == clean_user_key,
        )
        .first()
    )


# =========================================================
# UPDATE MEMORY
# =========================================================

def update_memory(
    db: Session,
    memory_id: int,
    value: Optional[str] = None,
    category: Optional[str] = None,
    importance: Optional[float] = None,
    user_key: str = DEFAULT_USER_KEY,
) -> Optional[Memory]:

    memory = get_memory_by_id(
        db=db,
        memory_id=memory_id,
        user_key=user_key,
    )

    if memory is None:
        return None

    value_changed = False
    category_changed = False

    # -----------------------------------------------------
    # VALUE
    # -----------------------------------------------------

    if value is not None:

        clean_value = _clean_whitespace(
            value
        )

        _validate_memory_text(
            key=memory.key,
            value=clean_value,
        )

        if memory.value != clean_value:
            memory.value = clean_value
            value_changed = True

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category is not None:

        clean_category = _normalize_category(
            category
        )

        if memory.category != clean_category:
            memory.category = clean_category
            category_changed = True

    # -----------------------------------------------------
    # IMPORTANCE
    # -----------------------------------------------------

    if importance is not None:
        memory.importance = _normalize_importance(
            importance
        )

    # -----------------------------------------------------
    # REGENERATE EMBEDDING
    # -----------------------------------------------------

    if value_changed or category_changed:

        memory_text = _build_memory_text(
            key=memory.key,
            value=memory.value,
            category=memory.category,
        )

        embedding = _generate_embedding(
            memory_text
        )

        embedding_json = _embedding_to_json(
            embedding
        )

        if embedding_json is not None:
            memory.embedding = embedding_json

    db.commit()
    db.refresh(memory)

    return memory


# =========================================================
# DELETE MEMORY
# =========================================================

def delete_memory(
    db: Session,
    memory_id: int,
    user_key: str = DEFAULT_USER_KEY,
) -> bool:

    memory = get_memory_by_id(
        db=db,
        memory_id=memory_id,
        user_key=user_key,
    )

    if memory is None:
        return False

    db.delete(memory)
    db.commit()

    return True


# =========================================================
# CLEAR MEMORIES
# =========================================================

def clear_memories(
    db: Session,
    user_key: str = DEFAULT_USER_KEY,
) -> int:

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    memories = (
        db.query(Memory)
        .filter(
            Memory.user_key == clean_user_key
        )
        .all()
    )

    count = len(memories)

    for memory in memories:
        db.delete(memory)

    db.commit()

    return count


# =========================================================
# COUNT MEMORIES
# =========================================================

def count_memories(
    db: Session,
    user_key: str = DEFAULT_USER_KEY,
) -> int:

    clean_user_key = (
        _clean_whitespace(
            user_key
        )
        or DEFAULT_USER_KEY
    )

    return (
        db.query(Memory)
        .filter(
            Memory.user_key == clean_user_key
        )
        .count()
    )