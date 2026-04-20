from datetime import datetime

from pydantic import BaseModel


class PostSummary(BaseModel):
    key: int | str
    title: str
    published: datetime | None
    path: str | None


class PostDetails(PostSummary):
    body: str
    updated: datetime | None
    tags: list[str]


class PostList(BaseModel):
    posts: list[PostSummary]
