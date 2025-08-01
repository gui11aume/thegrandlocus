from __future__ import annotations

import datetime
from datetime import timezone
from google.cloud import datastore
from models.blog_post import BlogPost
from config import settings
from typing import Optional
from utils import slugify


def format_post_path(post, num):
    """Make the address of the post."""

    slug: str = slugify(post.title)
    # Do not append 0, only greater integers.
    if num > 0:
        slug += "-" + str(num)
    date: datetime.datetime = post.published
    post_path_format: str = settings.post_path_format

    return post_path_format % {
        "slug": slug,
        "year": date.year,
        "month": date.month,
        "day": date.day,
    }


def get_post_by_id(post_id: int, db: datastore.Client):
    """Fetches a single post by its integer ID."""

    key = db.key("BlogPost", post_id)
    entity = db.get(key)
    if entity:
        return BlogPost.from_datastore_entity(entity)
    return None


def get_posts(
    db: datastore.Client,
    offset: int = 0,
    limit: Optional[int] = 20,
    published_only: bool = True,
    with_total: bool = False,
):
    """Fetches blog posts from Datastore.

    For the admin view (published_only=False), this function fetches all posts
    and sorts them in Python to handle drafts correctly (which may not have a
    'published' date). For the public view, it fetches paginated published posts
    directly from Datastore.
    """
    query = db.query(kind="BlogPost")
    total_posts = 0

    if published_only:
        now = datetime.datetime.now(datetime.timezone.utc)
        query.add_filter(property_name="published", operator="<=", value=now)
        query.order = ["-published"]

        if with_total:
            # Create a new query for counting without limit/offset
            count_query = db.query(kind="BlogPost")
            count_query.add_filter(property_name="published", operator="<=", value=now)
            # Use keys_only for efficiency
            total_posts = len(list(count_query.fetch()))

        entities = list(query.fetch(offset=offset, limit=limit))
        posts = [BlogPost.from_datastore_entity(entity) for entity in entities]

        if with_total:
            return posts, total_posts
        return posts
    else:
        # Admin view: fetch all posts, sort in Python, then paginate.
        all_entities = list(query.fetch())

        def sort_key(entity):
            published_date = entity.get("published")
            if published_date is None:
                # Give drafts a very recent timestamp to appear on top when sorted descending
                return datetime.datetime.now(
                    datetime.timezone.utc
                ) + datetime.timedelta(days=1)
            return published_date

        all_entities.sort(key=sort_key, reverse=True)

        paginated_entities = all_entities[offset : (offset + limit if limit else None)]
        posts = [
            BlogPost.from_datastore_entity(entity) for entity in paginated_entities
        ]

        if with_total:
            return posts, len(all_entities)
        return posts


def get_post_by_path(path: str, db: datastore.Client):
    """Fetches a single post by its path."""

    query = db.query(kind="BlogPost")
    query.add_filter(property_name="path", operator="=", value=path)
    posts = list(query.fetch(limit=1))
    if posts:
        return BlogPost.from_datastore_entity(posts[0])
    return None


def save_post(post: BlogPost, db: datastore.Client):
    """Create or update a BlogPost object in the Datastore."""

    # Properties with long text content that should not be indexed.
    exclude_from_indexes = ["body"]

    if post.key and post.key.id_or_name:
        # Existing post, use its key
        entity = datastore.Entity(key=post.key, exclude_from_indexes=exclude_from_indexes)
    else:
        # New post, create a new key
        key = db.key("BlogPost")
        entity = datastore.Entity(key=key, exclude_from_indexes=exclude_from_indexes)

        # Make sure path is unique
        if not post.path and post.published:
            # A bit of a chicken-and-egg problem for path generation,
            # so we pass the post to the path formatter.
            num = 0
            while True:
                path = format_post_path(post, num)
                # Check if path is already taken.
                existing_post = get_post_by_path(path, db)
                if not existing_post:
                    post.path = path
                    break
                num += 1

    post.slugs = [slugify(tag) for tag in post.tags]

    entity.update(
        {
            "title": post.title,
            "body": post.body,
            "published": post.published,
            "updated": post.updated or datetime.datetime.now(timezone.utc),
            "tags": post.tags,
            "difficulty": post.difficulty,
            "path": post.path,
            "slugs": post.slugs,
        }
    )
    db.put(entity)
    # Return the saved post with its key
    return BlogPost.from_datastore_entity(entity)


def delete_post(post_id: int, db: datastore.Client):
    """Deletes a post by its ID."""

    key = db.key("BlogPost", post_id)
    db.delete(key)


def get_posts_by_tag(
    tag: str,
    db: datastore.Client,
    limit: Optional[int] = 10,
    offset: int = 0,
    with_total: bool = False,
):
    """Fetches published blog posts with tag, sorted by publication date."""

    query = db.query(kind="BlogPost")
    query.add_filter("slugs", "=", tag)
    now = datetime.datetime.now(datetime.timezone.utc)
    query.add_filter("published", "<=", now)
    query.order = ["-published"]

    if with_total:
        count_query = db.query(kind="BlogPost")
        count_query.add_filter("slugs", "=", tag)
        count_query.add_filter("published", "<=", now)
        count_query.keys_only = True
        total_posts = len(list(count_query.fetch()))

        entities = list(query.fetch(offset=offset, limit=limit))
        posts = [BlogPost.from_datastore_entity(entity) for entity in entities]
        return posts, total_posts
    else:
        entities = list(query.fetch(offset=offset, limit=limit))
        posts = [BlogPost.from_datastore_entity(entity) for entity in entities]
        return posts
