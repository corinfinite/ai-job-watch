"""Utility functions for job scraping."""

import hashlib
import html
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional


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


class _MarkdownConverter(HTMLParser):
    """HTML to Markdown converter using Python's built-in parser."""

    def __init__(self):
        super().__init__()
        self.output: list[str] = []
        self.list_stack: list[str] = []  # Track nested lists ('ul' or 'ol')
        self.list_counters: list[int] = []  # Track ordered list counters
        self.current_link: Optional[str] = None
        self.in_pre = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.output.append(f"\n\n{'#' * level} ")
        elif tag == "p":
            self.output.append("\n\n")
        elif tag == "br":
            self.output.append("\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            self.current_link = attrs_dict.get("href", "")
            self.output.append("[")
        elif tag == "ul":
            self.list_stack.append("ul")
            self.output.append("\n")
        elif tag == "ol":
            self.list_stack.append("ol")
            self.list_counters.append(0)
            self.output.append("\n")
        elif tag == "li":
            indent = "  " * (len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ol":
                self.list_counters[-1] += 1
                self.output.append(f"{indent}{self.list_counters[-1]}. ")
            else:
                self.output.append(f"{indent}- ")
        elif tag == "pre":
            self.in_pre = True
            self.output.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.output.append("`")
        elif tag == "hr":
            self.output.append("\n\n---\n\n")
        elif tag == "blockquote":
            self.output.append("\n> ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.output.append("\n")
        elif tag == "p":
            self.output.append("\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            if self.current_link:
                self.output.append(f"]({self.current_link})")
            else:
                self.output.append("]")
            self.current_link = None
        elif tag == "ul":
            if self.list_stack and self.list_stack[-1] == "ul":
                self.list_stack.pop()
            self.output.append("\n")
        elif tag == "ol":
            if self.list_stack and self.list_stack[-1] == "ol":
                self.list_stack.pop()
                if self.list_counters:
                    self.list_counters.pop()
            self.output.append("\n")
        elif tag == "li":
            self.output.append("\n")
        elif tag == "pre":
            self.in_pre = False
            self.output.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.output.append("`")
        elif tag == "blockquote":
            self.output.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_pre:
            self.output.append(data)
        else:
            # Normalize whitespace but preserve single spaces
            text = re.sub(r"\s+", " ", data)
            self.output.append(text)

    def handle_entityref(self, name: str) -> None:
        char = html.unescape(f"&{name};")
        self.output.append(char)

    def handle_charref(self, name: str) -> None:
        char = html.unescape(f"&#{name};")
        self.output.append(char)

    def get_markdown(self) -> str:
        result = "".join(self.output)
        # Clean up excessive whitespace
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = re.sub(r" +", " ", result)
        # Clean up trailing spaces on lines
        result = re.sub(r" +\n", "\n", result)
        # Fix headers that have bold inside them (##**text** -> ## text)
        result = re.sub(r"(#{1,6}) \*\*(.+?)\*\*", r"\1 \2", result)
        # Remove colons at end of headers if they're the only formatting
        result = re.sub(r"(#{1,6} .+):\n", r"\1\n", result)
        return result.strip()


def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown using a proper parser.

    Handles common elements: headers, paragraphs, lists, links, bold/italic,
    code blocks, blockquotes, and horizontal rules.
    """
    converter = _MarkdownConverter()
    try:
        converter.feed(html_content)
        return converter.get_markdown()
    except Exception:
        # Fallback: just strip HTML tags
        return strip_html(html_content)


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
