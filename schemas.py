from pydantic import BaseModel
from datetime import datetime
from typing import Union, Optional


class PostSummary(BaseModel):
    key: Union[int, str]
    title: str
    published: Optional[datetime]
    path: Optional[str]


class PostDetails(PostSummary):
    body: str
    updated: Optional[datetime]
    tags: list[str]


class PostList(BaseModel):
    posts: list[PostSummary]
