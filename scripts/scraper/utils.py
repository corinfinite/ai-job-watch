"""Utility functions for job scraping."""

import hashlib
import html
import re
from datetime import datetime, timezone


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Example: "Engineering Manager, Claude" -> "engineering-manager-claude"
    """
    # Convert to lowercase
    text = text.lower()
    # Replace common separators with spaces
    text = re.sub(r"[,/&]", " ", text)
    # Remove anything that's not alphanumeric or space
    text = re.sub(r"[^\w\s-]", "", text)
    # Replace whitespace with hyphens
    text = re.sub(r"[-\s]+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    return text


def hash_description(text: str) -> str:
    """Generate a 12-character hash of description text.

    First strips HTML and normalizes whitespace.
    """
    cleaned = strip_html(text)
    cleaned = normalize_whitespace(cleaned)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return re.sub(r"\s+", " ", text).strip()


def html_to_markdown(html_content: str) -> str:
    """Convert HTML to simple Markdown.

    Handles common elements: headers, paragraphs, lists, links, bold/italic.
    """
    text = html_content

    # Handle line breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Headers
    for i in range(1, 7):
        text = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            r"\n" + "#" * i + r" \1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # Bold
    text = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE | re.DOTALL)

    # Italic
    text = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.IGNORECASE | re.DOTALL)

    # Links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.IGNORECASE | re.DOTALL)

    # Unordered lists
    text = re.sub(r"<ul[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</ul>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.IGNORECASE | re.DOTALL)

    # Ordered lists
    text = re.sub(r"<ol[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</ol>", "\n", text, flags=re.IGNORECASE)

    # Paragraphs
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL)

    # Divs and spans (just remove tags)
    text = re.sub(r"<div[^>]*>(.*?)</div>", r"\1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove any remaining tags
    text = strip_html(text)

    # Clean up excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def get_today_utc() -> str:
    """Get today's date in ISO format (YYYY-MM-DD) in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def format_date(date_str: str) -> str:
    """Format a date string to YYYY-MM-DD.

    Handles various input formats.
    """
    # If already in correct format, return as-is
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Return as-is if we can't parse
    return date_str
