import re
from typing import Dict, List


def extract_memories(
    message: str,
) -> List[Dict[str, object]]:
    """
    Detect useful long-term information from a user message.

    This version intentionally uses deterministic rules.
    It does not make an extra Gemini request.
    """

    text = message.strip()

    if not text:
        return []

    memories: List[Dict[str, object]] = []
    lowered = text.lower()

    # =========================================================
    # PROGRAMMING LANGUAGE — PYTHON
    # =========================================================

    if "python" in lowered and (
        "prefer" in lowered
        or "use" in lowered
        or "my language" in lowered
        or "programming language" in lowered
    ):
        memories.append(
            {
                "key": "programming_language",
                "value": "Python",
                "category": "preference",
                "importance": 0.90,
            }
        )

    # =========================================================
    # PROGRAMMING LANGUAGE — JAVASCRIPT
    # =========================================================

    if "javascript" in lowered and (
        "prefer" in lowered
        or "use" in lowered
        or "my language" in lowered
        or "programming language" in lowered
    ):
        memories.append(
            {
                "key": "programming_language",
                "value": "JavaScript",
                "category": "preference",
                "importance": 0.85,
            }
        )

    # =========================================================
    # PROGRAMMING LANGUAGE — TYPESCRIPT
    # =========================================================

    if "typescript" in lowered and (
        "prefer" in lowered
        or "use" in lowered
        or "my language" in lowered
        or "programming language" in lowered
    ):
        memories.append(
            {
                "key": "programming_language",
                "value": "TypeScript",
                "category": "preference",
                "importance": 0.85,
            }
        )

    # =========================================================
    # FRAMEWORK — FASTAPI
    # =========================================================

    if "fastapi" in lowered and (
        "prefer" in lowered
        or "use" in lowered
        or "framework" in lowered
    ):
        memories.append(
            {
                "key": "framework",
                "value": "FastAPI",
                "category": "preference",
                "importance": 0.90,
            }
        )

    # =========================================================
    # FRAMEWORK — NEXT.JS
    # =========================================================

    if "next.js" in lowered or "nextjs" in lowered:
        if (
            "use" in lowered
            or "prefer" in lowered
            or "frontend" in lowered
            or "project" in lowered
        ):
            memories.append(
                {
                    "key": "frontend_framework",
                    "value": "Next.js",
                    "category": "technical_preference",
                    "importance": 0.85,
                }
            )

    # =========================================================
    # DATABASE — SQLITE
    # =========================================================

    if "sqlite" in lowered and (
        "use" in lowered
        or "database" in lowered
        or "prefer" in lowered
        or "project" in lowered
    ):
        memories.append(
            {
                "key": "database",
                "value": "SQLite",
                "category": "technical_preference",
                "importance": 0.75,
            }
        )

    # =========================================================
    # PROJECT NAME
    #
    # Examples:
    # My project is IGNYX
    # My project is called IGNYX AI
    # The project is called IGNYX
    # =========================================================

    project_patterns = [
        r"\bmy\s+project\s+is\s+called\s+([A-Za-z0-9 _.-]{2,80})",
        r"\bmy\s+project\s+is\s+([A-Za-z0-9 _.-]{2,80})",
        r"\bthe\s+project\s+is\s+called\s+([A-Za-z0-9 _.-]{2,80})",
    ]

    for pattern in project_patterns:
        project_match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if project_match:
            project_name = (
                project_match.group(1)
                .strip()
                .rstrip(".")
            )

            if project_name:
                memories.append(
                    {
                        "key": "project",
                        "value": project_name,
                        "category": "project",
                        "importance": 0.90,
                    }
                )

            break

    # =========================================================
    # USER NAME
    #
    # Example:
    # My name is Mathan
    # =========================================================

    name_match = re.search(
        r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z .'-]{1,60})",
        text,
        flags=re.IGNORECASE,
    )

    if name_match:
        name = (
            name_match.group(1)
            .strip()
            .rstrip(".")
        )

        if name:
            memories.append(
                {
                    "key": "name",
                    "value": name,
                    "category": "profile",
                    "importance": 0.95,
                }
            )

    # =========================================================
    # LOCATION
    #
    # Examples:
    # I live in Chennai
    # I'm from Chennai
    # I am from Chennai
    # =========================================================

    location_match = re.search(
        r"\b(?:i\s+live\s+in|i\s+am\s+from|i'm\s+from)\s+([A-Za-z .'-]{2,60})",
        text,
        flags=re.IGNORECASE,
    )

    if location_match:
        location = (
            location_match.group(1)
            .strip()
            .rstrip(".")
        )

        if location:
            memories.append(
                {
                    "key": "location",
                    "value": location,
                    "category": "profile",
                    "importance": 0.75,
                }
            )

    # =========================================================
    # RESPONSE STYLE PREFERENCE
    #
    # Example:
    # I prefer concise answers
    # I like detailed explanations
    # =========================================================

    if (
        "prefer concise" in lowered
        or "prefer short answers" in lowered
        or "keep answers concise" in lowered
    ):
        memories.append(
            {
                "key": "response_style",
                "value": "concise",
                "category": "preference",
                "importance": 0.80,
            }
        )

    if (
        "prefer detailed" in lowered
        or "prefer detailed explanations" in lowered
        or "give detailed answers" in lowered
    ):
        memories.append(
            {
                "key": "response_style",
                "value": "detailed",
                "category": "preference",
                "importance": 0.80,
            }
        )

    # =========================================================
    # UI / THEME PREFERENCE — DARK MODE
    #
    # Examples:
    # I prefer dark mode
    # I prefer dark mode interfaces
    # Remember that I prefer dark mode interfaces
    # I like dark themes
    # Use dark mode for my applications
    # I prefer dark UI
    # =========================================================

    dark_mode_indicators = (
        "dark mode",
        "dark theme",
        "dark ui",
        "dark interface",
        "dark interfaces",
        "dark design",
    )

    dark_mode_preference_words = (
        "prefer",
        "preference",
        "like",
        "love",
        "want",
        "use",
        "choose",
        "remember",
        "remember that",
        "favor",
        "favour",
    )

    if (
        any(indicator in lowered for indicator in dark_mode_indicators)
        and any(word in lowered for word in dark_mode_preference_words)
    ):
        memories.append(
            {
                "key": "ui_theme",
                "value": "dark",
                "category": "ui_preference",
                "importance": 0.85,
            }
        )

    # =========================================================
    # UI / THEME PREFERENCE — LIGHT MODE
    #
    # Examples:
    # I prefer light mode
    # I like light themes
    # Remember that I prefer light interfaces
    # =========================================================

    light_mode_indicators = (
        "light mode",
        "light theme",
        "light ui",
        "light interface",
        "light interfaces",
        "light design",
    )

    if (
        any(indicator in lowered for indicator in light_mode_indicators)
        and any(word in lowered for word in dark_mode_preference_words)
    ):
        memories.append(
            {
                "key": "ui_theme",
                "value": "light",
                "category": "ui_preference",
                "importance": 0.85,
            }
        )

    # =========================================================
    # UI / THEME PREFERENCE — SYSTEM / AUTO
    #
    # Examples:
    # Use system theme
    # I prefer automatic theme
    # Follow system mode
    # =========================================================

    system_theme_indicators = (
        "system theme",
        "system mode",
        "automatic theme",
        "auto theme",
        "follow system",
        "system preference",
        "system appearance",
    )

    if (
        any(indicator in lowered for indicator in system_theme_indicators)
        and any(word in lowered for word in dark_mode_preference_words)
    ):
        memories.append(
            {
                "key": "ui_theme",
                "value": "system",
                "category": "ui_preference",
                "importance": 0.80,
            }
        )

    # =========================================================
    # COMMAND / SHELL PREFERENCE
    # =========================================================

    if "powershell" in lowered and (
        "prefer" in lowered
        or "use" in lowered
        or "commands" in lowered
    ):
        memories.append(
            {
                "key": "shell",
                "value": "PowerShell",
                "category": "technical_preference",
                "importance": 0.75,
            }
        )

    # =========================================================
    # GENERAL REMEMBER / PREFERENCE PATTERNS
    #
    # These provide a small amount of extra coverage for
    # explicit user preferences that don't need a dedicated
    # domain-specific detector.
    # =========================================================

    general_preference_patterns = [
        (
            r"\b(?:i\s+prefer|i\s+like|i\s+love|i\s+favor|i\s+favour)\s+"
            r"(?:using|having|working\s+with)\s+([^.!?\n]{3,100})",
            "general_preference",
        ),
    ]

    for pattern, key in general_preference_patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            value = match.group(1).strip().rstrip(".!?")

            if value:
                memories.append(
                    {
                        "key": key,
                        "value": value,
                        "category": "preference",
                        "importance": 0.65,
                    }
                )

    # =========================================================
    # REMOVE DUPLICATE KEYS
    #
    # Latest detected value wins.
    # =========================================================

    unique_memories: Dict[
        str,
        Dict[str, object],
    ] = {}

    for memory in memories:
        key = str(
            memory.get("key", "")
        ).strip()

        if key:
            unique_memories[key] = memory

    return list(
        unique_memories.values()
    )