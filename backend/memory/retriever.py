import json
import math
from typing import List, Dict, Any, Tuple

from sqlalchemy.orm import Session

from memory.models import Memory


DEFAULT_USER_KEY = "default_user"


# =========================================================
# RELEVANCE SETTINGS
# =========================================================

MIN_SEMANTIC_SIMILARITY = 0.50
MIN_HYBRID_SCORE = 0.48
MIN_KEYWORD_SCORE = 0.20

# Candidate must have some meaningful topic relationship
# with the query unless the semantic match is extremely strong.
STRONG_SEMANTIC_SIMILARITY = 0.78


# =========================================================
# TOPIC / INTENT GROUPS
# =========================================================

TOPIC_GROUPS = {
    "technology": {
        "technology",
        "technologies",
        "tech",
        "stack",
        "framework",
        "frameworks",
        "language",
        "languages",
        "programming",
        "coding",
        "backend",
        "frontend",
        "development",
        "developer",
        "software",
        "database",
        "databases",
    },

    "ui": {
        "ui",
        "theme",
        "themes",
        "appearance",
        "design",
        "interface",
        "interfaces",
        "visual",
        "style",
        "styles",
        "dark",
        "light",
        "mode",
    },

    "profile": {
        "name",
        "called",
        "live",
        "location",
        "from",
        "city",
    },

    "project": {
        "project",
        "projects",
        "ignyx",
    },

    "response": {
        "answer",
        "answers",
        "response",
        "responses",
        "explanation",
        "explanations",
        "concise",
        "detailed",
    },

    "shell": {
        "shell",
        "terminal",
        "command",
        "commands",
        "powershell",
        "console",
    },
}


MEMORY_TOPIC_MAP = {
    "programming_language": "technology",
    "framework": "technology",
    "frontend_framework": "technology",
    "database": "technology",

    "ui_theme": "ui",

    "name": "profile",
    "location": "profile",

    "project": "project",

    "response_style": "response",

    "shell": "shell",
}


# =========================================================
# TEXT HELPERS
# =========================================================

def _normalize_text(
    value: str,
) -> str:
    return " ".join(
        value.lower().strip().split()
    )


def _tokenize(
    value: str,
) -> set[str]:
    normalized = _normalize_text(
        value
    )

    return {
        token
        for token in normalized.split()
        if len(token) >= 2
    }


# =========================================================
# QUERY TOPIC DETECTION
# =========================================================

def _detect_query_topics(
    query: str,
) -> set[str]:
    """
    Identify broad topics represented in the user's query.
    """

    tokens = _tokenize(
        query
    )

    topics = set()

    for topic, keywords in TOPIC_GROUPS.items():
        if tokens.intersection(
            keywords
        ):
            topics.add(topic)

    return topics


def _memory_topic(
    memory: Memory,
) -> str | None:
    return MEMORY_TOPIC_MAP.get(
        memory.key
    )


def _topic_match_score(
    memory: Memory,
    query: str,
) -> float:
    """
    Score topic/lexical relationship.

    Returns:
        1.0 = strong topic match
        0.5 = partial lexical relationship
        0.0 = no topic relationship
    """

    query_topics = _detect_query_topics(
        query
    )

    if not query_topics:
        return 0.0

    memory_topic = _memory_topic(
        memory
    )

    if (
        memory_topic
        and memory_topic in query_topics
    ):
        return 1.0

    # Fall back to direct token overlap.
    query_tokens = _tokenize(
        query
    )

    searchable_text = " ".join(
        [
            memory.category or "",
            memory.key or "",
            memory.value or "",
        ]
    )

    memory_tokens = _tokenize(
        searchable_text
    )

    overlap = query_tokens.intersection(
        memory_tokens
    )

    if overlap:
        return min(
            0.5 + (
                len(overlap) * 0.10
            ),
            0.90,
        )

    return 0.0


# =========================================================
# KEYWORD SCORE
# =========================================================

def calculate_memory_score(
    memory: Memory,
    query: str,
) -> float:
    """
    Deterministic keyword relevance score.
    """

    query_tokens = _tokenize(
        query
    )

    if not query_tokens:
        return 0.0

    searchable_text = " ".join(
        [
            memory.category or "",
            memory.key or "",
            memory.value or "",
        ]
    )

    memory_tokens = _tokenize(
        searchable_text
    )

    if not memory_tokens:
        return 0.0

    overlap = query_tokens.intersection(
        memory_tokens
    )

    overlap_score = (
        len(overlap)
        / max(
            len(query_tokens),
            1,
        )
    )

    importance = float(
        memory.importance or 0.0
    )

    return (
        (overlap_score * 0.80)
        + (importance * 0.20)
    )


# =========================================================
# STORED EMBEDDING HELPERS
# =========================================================

def _parse_embedding(
    value: Any,
) -> List[float]:
    if not value:
        return []

    try:
        parsed = json.loads(
            value
        )

        if not isinstance(
            parsed,
            list,
        ):
            return []

        return [
            float(item)
            for item in parsed
        ]

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return []


def _cosine_similarity(
    first: List[float],
    second: List[float],
) -> float:
    if not first or not second:
        return 0.0

    if len(first) != len(second):
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(
            first,
            second,
        )
    )

    first_norm = math.sqrt(
        sum(
            a * a
            for a in first
        )
    )

    second_norm = math.sqrt(
        sum(
            b * b
            for b in second
        )
    )

    if first_norm == 0.0:
        return 0.0

    if second_norm == 0.0:
        return 0.0

    similarity = (
        dot_product
        / (
            first_norm
            * second_norm
        )
    )

    return max(
        -1.0,
        min(
            similarity,
            1.0,
        ),
    )


def calculate_semantic_similarity(
    memory: Memory,
    query_embedding: List[float],
) -> float:
    if not query_embedding:
        return 0.0

    if not memory.embedding:
        return 0.0

    memory_embedding = _parse_embedding(
        memory.embedding
    )

    if not memory_embedding:
        return 0.0

    return max(
        _cosine_similarity(
            query_embedding,
            memory_embedding,
        ),
        0.0,
    )


# =========================================================
# HYBRID SCORE
# =========================================================

def calculate_hybrid_memory_score(
    memory: Memory,
    query: str,
    query_embedding: List[float],
) -> float:
    """
    Combined score:

        semantic = 55%
        keyword  = 25%
        topic    = 15%
        importance = 5%
    """

    semantic_score = calculate_semantic_similarity(
        memory,
        query_embedding,
    )

    keyword_score = calculate_memory_score(
        memory,
        query,
    )

    topic_score = _topic_match_score(
        memory,
        query,
    )

    importance = float(
        memory.importance or 0.0
    )

    return (
        (semantic_score * 0.55)
        + (keyword_score * 0.25)
        + (topic_score * 0.15)
        + (importance * 0.05)
    )


# =========================================================
# QUERY EMBEDDING
# =========================================================

def _generate_query_embedding(
    query: str,
) -> List[float]:

    try:
        from memory.manager import _generate_embedding

        embedding = _generate_embedding(
            query
        )

        if embedding:
            return embedding

    except Exception as exc:
        print(
            f"[MEMORY] Query embedding unavailable: {exc}"
        )

    return []


# =========================================================
# CANDIDATE RELEVANCE
# =========================================================

def _is_relevant_candidate(
    memory: Memory,
    query: str,
    query_embedding: List[float],
    score: float,
) -> bool:

    topic_score = _topic_match_score(
        memory,
        query,
    )

    semantic_score = calculate_semantic_similarity(
        memory,
        query_embedding,
    )

    # -----------------------------------------------------
    # Strong semantic match can stand on its own.
    # -----------------------------------------------------

    if (
        semantic_score
        >= STRONG_SEMANTIC_SIMILARITY
    ):
        return score >= MIN_HYBRID_SCORE

    # -----------------------------------------------------
    # Normal semantic match requires topic evidence.
    # -----------------------------------------------------

    if (
        semantic_score
        >= MIN_SEMANTIC_SIMILARITY
        and topic_score > 0
        and score >= MIN_HYBRID_SCORE
    ):
        return True

    # -----------------------------------------------------
    # Keyword fallback.
    # -----------------------------------------------------

    keyword_score = calculate_memory_score(
        memory,
        query,
    )

    if (
        topic_score > 0
        and keyword_score >= MIN_KEYWORD_SCORE
    ):
        return True

    return False


# =========================================================
# RETRIEVE RELEVANT MEMORIES
# =========================================================

def retrieve_relevant_memories(
    db: Session,
    query: str,
    user_key: str = DEFAULT_USER_KEY,
    limit: int = 5,
) -> List[Memory]:

    clean_query = _normalize_text(
        query
    )

    if not clean_query:
        return []

    if limit <= 0:
        return []

    memories = (
        db.query(Memory)
        .filter(
            Memory.user_key == user_key
        )
        .order_by(
            Memory.importance.desc(),
            Memory.updated_at.desc(),
        )
        .all()
    )

    if not memories:
        return []

    query_embedding = _generate_query_embedding(
        clean_query
    )

    # =====================================================
    # SEMANTIC PATH
    # =====================================================

    if query_embedding:

        candidates: List[
            Tuple[
                float,
                float,
                float,
                Memory,
            ]
        ] = []

        for memory in memories:

            semantic_score = calculate_semantic_similarity(
                memory,
                query_embedding,
            )

            score = calculate_hybrid_memory_score(
                memory=memory,
                query=clean_query,
                query_embedding=query_embedding,
            )

            topic_score = _topic_match_score(
                memory,
                clean_query,
            )

            if not _is_relevant_candidate(
                memory=memory,
                query=clean_query,
                query_embedding=query_embedding,
                score=score,
            ):
                continue

            candidates.append(
                (
                    score,
                    semantic_score,
                    topic_score,
                    memory,
                )
            )

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                item[3].importance or 0.0,
            ),
            reverse=True,
        )

        return [
            memory
            for _, _, _, memory
            in candidates[:limit]
        ]

    # =====================================================
    # KEYWORD FALLBACK
    # =====================================================

    keyword_candidates = []

    for memory in memories:

        score = calculate_memory_score(
            memory,
            clean_query,
        )

        topic_score = _topic_match_score(
            memory,
            clean_query,
        )

        if (
            score < MIN_KEYWORD_SCORE
            or topic_score <= 0
        ):
            continue

        keyword_candidates.append(
            (
                score,
                topic_score,
                memory,
            )
        )

    keyword_candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].importance or 0.0,
        ),
        reverse=True,
    )

    return [
        memory
        for _, _, memory
        in keyword_candidates[:limit]
    ]


# =========================================================
# MEMORY → PROMPT CONTEXT
# =========================================================

def memories_to_context(
    memories: List[Memory],
) -> str:

    if not memories:
        return ""

    lines = [
        "\n\nRELEVANT LONG-TERM MEMORY:",
        "Use these memories only when relevant to the user's current request.",
        "Do not mention the memory system unless the user asks.",
        "",
    ]

    for memory in memories:
        lines.append(
            f"- [{memory.category}] "
            f"{memory.key}: {memory.value}"
        )

    return "\n".join(
        lines
    )


# =========================================================
# COMPLETE MEMORY RETRIEVAL
# =========================================================

def retrieve_memory_context(
    db: Session,
    query: str,
    user_key: str = DEFAULT_USER_KEY,
    limit: int = 5,
) -> Dict[str, Any]:

    memories = retrieve_relevant_memories(
        db=db,
        query=query,
        user_key=user_key,
        limit=limit,
    )

    return {
        "memories": memories,
        "context": memories_to_context(
            memories
        ),
        "count": len(memories),
    }