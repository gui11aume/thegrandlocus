import datetime
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
import re

from google.cloud import datastore
from utils import HTMLWordTruncator, slugify


class SourceCodePreprocessor(Preprocessor):
    """
    This preprocessor converts [sourcecode:language]...[/sourcecode]
    blocks into Markdown's fenced code blocks.
    """

    pattern = re.compile(
        r"\[sourcecode:(?P<lang>[a-zA-Z0-9_+-]+)\](?P<code>.*?)\[/sourcecode\]",
        re.DOTALL | re.IGNORECASE,
    )

    def sub_fenced_code(self, match: re.Match) -> str:
        lang = match.group("lang").lower()
        code = match.group("code")
        if lang in ["py", "r"]:
            return f'```{{ .{lang} linenos=true }}\n{code}\n```'
        return f"```{lang}\n{code}\n```"

    def run(self, lines: list[str]) -> list[str]:
        text = "\n".join(lines)
        new_text = self.pattern.sub(self.sub_fenced_code, text)
        return new_text.split("\n")


class SourceCodeExtension(Extension):
    """
    An extension to register the SourceCodePreprocessor.
    """

    def extendMarkdown(self, md):
        md.preprocessors.register(
            SourceCodePreprocessor(md), "sourcecode", 175
        )


class BlogPost:
    def __init__(
        self,
        key,
        title: str,
        body: str,
        published: datetime.datetime,
        updated: datetime.datetime,
        path: str = "",
        tags: list = [],
        difficulty: int = 0,
        slugs: list = [],
    ) -> None:
        self.key = key
        self.title = title
        self.body = body
        self.published = published
        self.updated = updated
        self.path = path
        self.tags = tags if tags is not None else []
        self.difficulty = difficulty
        self.slugs = slugs if slugs is not None else []

    @property
    def published_tz(self) -> datetime.datetime:
        return self.published  # Assume UTC.

    @property
    def tag_pairs(self) -> list[tuple[str, str]]:
        return [(tag, slugify(tag)) for tag in self.tags]

    @property
    def summary(self) -> str:
        html = markdown.markdown(self.body, extensions=["md_in_html"])
        truncator = HTMLWordTruncator(max_words=180, end="__TRUNCATION_MARKER_")
        truncated = truncator.process(html)
        # There can be a space before the truncation marker, so we remove it.
        return re.sub(r"\s*__TRUNCATION_MARKER_", "...", truncated)

    @property
    def rendered(self) -> str:
        return markdown.markdown(
            self.body,
            extensions=[
                SourceCodeExtension(),
                "fenced_code",
                "codehilite",
                "tables",
                "attr_list",
                "md_in_html",
            ],
            extension_configs={
                "codehilite": {
                    "linenums": False,
                    "css_class": "codehilite",
                    "guess_lang": False,
                }
            },
        )

    @staticmethod
    def from_datastore_entity(entity: datastore.Entity) -> "BlogPost":
        return BlogPost(
            key=entity.key,
            title=entity.get("title"),
            body=entity.get("body"),
            published=entity.get("published"),
            updated=entity.get("updated"),
            path=entity.get("path"),
            tags=entity.get("tags", []),
            difficulty=entity.get("difficulty", 0),
            slugs=entity.get("slugs", []),
        )

    def to_dict(self) -> dict:
        """Returns a dict representation of the BlogPost."""
        return {
            "id": self.key.id_or_name if self.key else None,
            "title": self.title,
            "body": self.body,
            "published": self.published.isoformat() if self.published else None,
            "updated": self.updated.isoformat() if self.updated else None,
            "path": self.path,
            "tags": self.tags,
            "difficulty": self.difficulty,
            "slugs": self.slugs,
        }

    def __repr__(self) -> str:
        return (
            f"BlogPost(key={self.key}, title={self.title}, published={self.published})"
        )
