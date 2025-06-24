import datetime
import markdown
import re

from google.cloud import datastore
from utils import HTMLWordTruncator


# A simple slugify function for tags
def slugify(value):
    return value.lower().strip().replace(" ", "-")


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
    ) -> None:
        self.key = key
        self.title = title
        self.body = body
        self.published = published
        self.updated = updated
        self.path = path
        self.tags = tags if tags is not None else []
        self.difficulty = difficulty

    @property
    def published_tz(self) -> datetime.datetime:
        return self.published  # Assume UTC.

    @property
    def tag_pairs(self) -> list[tuple[str, str]]:
        return [(tag, slugify(tag)) for tag in self.tags]

    @property
    def summary(self) -> str:
        html = markdown.markdown(self.body)
        truncator = HTMLWordTruncator(max_words=180, end="__TRUNCATION_MARKER_")
        truncated = truncator.process(html)
        # There can be a space before the truncation marker, so we remove it.
        return re.sub(r"\s*__TRUNCATION_MARKER_", "...", truncated)

    @property
    def rendered(self) -> str:
        return markdown.markdown(self.body)

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
        )

    def __repr__(self) -> str:
        return (
            f"BlogPost(key={self.key}, title={self.title}, published={self.published})"
        )
