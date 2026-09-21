"""Text utilities for the Phase 1 fixture project."""

from typing import Optional


def slugify(text: str) -> str:
    """Convert text to a lowercase slug with hyphens.

    Args:
        text: The input text.

    Returns:
        A slug: lowercase, non-alphanumeric chars collapsed to single hyphens,
        trimmed of leading/trailing hyphens.
    """
    result = []
    prev_hyphen = False
    for ch in text.lower():
        if ch.isalnum():
            result.append(ch)
            prev_hyphen = False
        else:
            if not prev_hyphen and result:
                result.append("-")
                prev_hyphen = True
    return "".join(result).strip("-")


def word_count(text: str) -> int:
    """Count words in text (whitespace-separated tokens)."""
    return len(text.split())


def truncate(text: str, max_length: int, suffix: str = "…") -> str:
    """Truncate text to max_length, appending suffix if truncated.

    Args:
        text: Input text.
        max_length: Maximum total length including suffix.
        suffix: Suffix to append when truncating.

    Returns:
        The original text if it fits, else truncated text + suffix.
    """
    if len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[: max_length - len(suffix)] + suffix


def find_first(text: str, target: str) -> Optional[int]:
    """Return the index of the first occurrence of target, or None."""
    idx = text.find(target)
    return idx if idx != -1 else None
