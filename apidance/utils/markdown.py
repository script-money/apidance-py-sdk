"""Markdown parsing utilities."""

import re
from dataclasses import dataclass
from typing import List, Set, Tuple, Dict, Any


@dataclass
class Mark:
    start: int  # Start position in original text
    end: int  # End position in original text
    types: Set[str]  # Formatting types (Bold/Italic)


def parse_markdown_to_richtext(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Parse markdown text to plain text and richtext tags.

    Args:
        text: Input text with markdown formatting

    Returns:
        Tuple of (plain text without markdown, list of richtext tags)
        Each tag contains:
        - from_index: start position in plain text
        - to_index: end position in plain text
        - richtext_types: list of formatting types (Bold/Italic)
    """

    def find_marks(pattern: str, text: str, mark_type: str) -> List[Mark]:
        """Find all non-overlapping markdown marks in text.

        Args:
            pattern: Regex pattern to match markdown
            text: Input text
            mark_type: Type of formatting (Bold/Italic)

        Returns:
            List of Mark objects with positions and types
        """
        marks = []
        last_end = 0

        for match in re.finditer(pattern, text):
            if match.start() >= last_end:
                marks.append(Mark(match.start(), match.end(), {mark_type}))
                last_end = match.end()
        return marks

    # Find all markdown marks
    marks = []

    # Bold: **text** or __text__
    marks.extend(
        find_marks(r"(?<!\*)\*\*([^*]+?)\*\*(?!\*)|__([^_]+?)__", text, "Bold")
    )

    # Italic: *text* or _text_
    marks.extend(
        find_marks(r"(?<!\*)\*([^*]+?)\*(?!\*)|(?<!_)_([^_]+?)_(?!_)", text, "Italic")
    )

    # Sort marks by position
    marks.sort(key=lambda x: (x.start, x.end))

    # Process marks and build plain text
    plain_text = text
    offset = 0
    richtext_tags = []

    for mark in marks:
        # Calculate positions in plain text
        real_start = mark.start - offset
        content_start = mark.start + (2 if "Bold" in mark.types else 1)
        content_end = mark.end - (2 if "Bold" in mark.types else 1)
        content = text[content_start:content_end]

        # Add tag
        richtext_tags.append(
            {
                "from_index": real_start,
                "to_index": real_start + len(content),
                "richtext_types": sorted(list(mark.types)),
            }
        )

        # Update text and offset
        plain_text = (
            plain_text[: mark.start - offset]
            + content
            + plain_text[mark.end - offset :]
        )
        offset += mark.end - mark.start - len(content)

    return plain_text, richtext_tags
