import re
from io import StringIO
from html.parser import HTMLParser
from typing import List, Optional, Set, Tuple
import unicodedata

VOID: Set[str] = {
    "area",
    "base",
    "br",
    "col",
    "command",
    "embed",
    "hr",
    "img",
    "input",
    "keygen",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class StopStreaming(Exception):
    """Exception used to interrupt HTML streaming."""


class HTMLStreamer(HTMLParser):
    """Basic HTML stream parser that redirects HTML to output stream.

    Args:
        out: Output stream (defaults to StringIO)
    """

    def __init__(self, out: StringIO = StringIO()) -> None:
        super().__init__(convert_charrefs=False)
        self.out: StringIO = out
        self.stack: List[str] = []

    def handle_charref(self, name: str) -> None:
        self.out.write(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.out.write(f"<!--{data}-->")

    def handle_data(self, data: str) -> None:
        self.out.write(data)

    def handle_decl(self, decl: str) -> None:
        self.out.write(f"<!{decl}>")

    def handle_endtag(self, tag: str) -> None:
        self.out.write(f"</{tag}>")
        if tag in VOID:
            return
        if self.stack and tag == self.stack[-1]:
            self.stack.pop()

    def handle_entityref(self, name: str) -> None:
        self.out.write(f"&{name};")

    def handle_pi(self, data: str) -> None:
        self.out.write(f"<?{data}>")

    def handle_startendtag(
        self, tag: str, attrs: List[Tuple[str, Optional[str]]]
    ) -> None:
        self.out.write(self.get_starttag_text())  # type: ignore

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.out.write(self.get_starttag_text())  # type: ignore
        if tag not in VOID:
            self.stack.append(tag)

    def close_open_tags(self) -> None:
        """Close all open tags in the stack."""
        for tag in reversed(self.stack):
            self.out.write(f"</{tag}>")

    def process(self, html: str) -> str:
        """Parse HTML and return as string.

        Args:
            html: HTML content to parse

        Returns:
            Processed HTML as string
        """
        self.reset()
        self.stack.clear()
        self.out = StringIO()
        try:
            self.feed(html)
        except StopStreaming:
            pass
        return self.out.getvalue()


class HTMLWordTruncator(HTMLStreamer):
    r"""Truncates HTML content after specified number of words.

    Handles multiple complex cases:
    - Preserves HTML structure while truncating
    - Properly counts hyphenated words as single words
    - Handles whitespace-only tokens without counting them as words
    - Maintains HTML tag integrity when truncating mid-tag
    - Processes unicode characters correctly
    - Handles self-closing tags like <img> and <br>
    - Preserves attributes with special characters

    Does not handle:
    - Truncation before a tag, preserving the space.

    Examples:
        ```python
        html = "one two <b>three</b> four"
        HTMLWordTruncator(max_words=1).process(html)
        # Output: "one__TRUNCATION_MARKER_" /no space/

        HTMLWordTruncator(max_words=2).process(html)
        # Output: "one two __TRUNCATION_MARKER_" /space/

        HTMLWordTruncator(max_words=3).process(html)
        # Output: "one two <b>three__TRUNCATION_MARKER_</b>" /no space/
        ```

    It is recommended to post-process the output to remove the
    truncation marker together with spaces before the tag, e.g., with
    `re.sub(r"\s*__TRUNCATION_MARKER_", "...", html)`.

    Args:
        max_words: Maximum number of words to allow
        end: String to append at truncation point
    """

    def __init__(
        self,
        max_words: Optional[int] = None,
        end: str = "__TRUNCATION_MARKER_",
    ) -> None:
        super().__init__()
        self.max_words: float = float("inf") if max_words is None else max_words
        self.end: str = end
        # Regex splits text into tokens: alternating non-word and word tokens
        # Captures word tokens (sequences of word chars/hyphens) for counting.
        self._splitter = re.compile(r"([\w-]+)")

    def handle_data(self, data: str) -> None:
        """Count words and truncate when exceeding limit.

        Handles cases:
        - Leading/trailing whitespace
        - Mixed content with tags and text
        - Unicode characters
        - Words with apostrophes
        - Whitespace-only tokens
        """
        # Check if word limit already reached
        if self.max_words <= 0:
            self.out.write(self.end)
            raise StopStreaming()

        # Split data into tokens while preserving whitespace
        parts = self._splitter.split(data)
        # Extract only word tokens (non-whitespace)
        word_tokens = [
            part for i, part in enumerate(parts) if i % 2 == 1 and part.strip()
        ]
        word_count = len(word_tokens)

        # Case 1: Entire chunk fits within remaining word limit
        if word_count <= self.max_words:
            self.out.write(data)
            self.max_words -= word_count
            return

        # Case 2: Need to truncate within this chunk
        output_parts = []
        words_taken = 0
        for i, part in enumerate(parts):
            output_parts.append(part)
            # Only count non-whitespace tokens as words
            if i % 2 == 1 and part.strip():
                words_taken += 1
                if words_taken == self.max_words:
                    break

        # Write truncated content
        self.out.write("".join(output_parts))
        self.out.write(self.end)
        self.close_open_tags()
        raise StopStreaming

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags - stop processing if limit reached."""
        if self.max_words <= 0:
            if self.stack:
                self.out.write(self.end)
                self.close_open_tags()
            raise StopStreaming
        super().handle_endtag(tag)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """Handle opening tags - stop processing if limit reached."""
        if self.max_words <= 0:
            self.out.write(self.end)
            self.close_open_tags()
            raise StopStreaming
        super().handle_starttag(tag, attrs)


def slugify(s: str) -> str:
    """Slugify a unicode string (replace non-letters and numbers with "-")."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower()).strip("-")
