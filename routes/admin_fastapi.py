import os
from typing import List
import datetime

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from google.cloud import datastore

from models.blog_post import BlogPost
from services import blog as blog_service
from services.datastore import get_datastore_client

admin_router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Dependency to check if user is authenticated
async def get_current_user(request: Request):
    if os.environ.get("DEV_MODE") == "true":
        return {
            "name": "Dev User",
            "email": "dev@example.com",
            "picture": "/static/images/me.jpg",
        }
    user = request.session.get("user")
    if not user:
        # This will redirect to the login page if not authenticated.
        return RedirectResponse(url="/login")
    return user


@admin_router.get("/", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: dict = Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user

    posts: List[BlogPost] = blog_service.get_posts(db, published_only=False, limit=None)
    offset = 0
    last_post = len(posts) - 1

    template_vals = {
        "request": request,
        "posts": posts,
        "now": datetime.datetime.now(datetime.timezone.utc),
        "user": user,
        "offset": offset,
        "last_post": last_post,
    }
    return templates.TemplateResponse("admin/index.html", template_vals)


@admin_router.get("/newpost/", response_class=HTMLResponse)
async def new_post_form(request: Request, user: dict = Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(
        "admin/edit.html",
        {
            "request": request,
            "post": None,
            "now": datetime.datetime.now(datetime.timezone.utc),
            "user": user,
        },
    )


@admin_router.get("/post/{post_id}", response_class=HTMLResponse)
async def edit_post_form(
    request: Request,
    post_id: int,
    user: dict = Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user
    post = blog_service.get_post_by_id(post_id, db)
    return templates.TemplateResponse(
        "admin/edit.html",
        {
            "request": request,
            "post": post,
            "now": datetime.datetime.now(datetime.timezone.utc),
            "user": user,
        },
    )


@admin_router.post("/newpost/", response_class=HTMLResponse)
async def create_post(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    tags: str = Form(""),
    difficulty: int = Form(0),
    draft: str = Form(None),
    user: dict = Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user
    post_is_draft = draft is not None

    if post_is_draft:
        # Using a far-future date for drafts
        published = datetime.datetime(9999, 12, 31)
        updated = datetime.datetime(9999, 12, 31)
    else:
        published = datetime.datetime.now(datetime.timezone.utc)
        updated = datetime.datetime.now(datetime.timezone.utc)

    post = BlogPost(
        key=None,
        title=title,
        body=body,
        published=published,
        updated=updated,
        path="",
        tags=[],
        difficulty=difficulty,
    )

    post.tags = [tag.strip() for tag in tags.split("\n") if tag.strip()]

    saved_post = blog_service.save_post(post, db)
    return templates.TemplateResponse(
        "admin/published.html",
        {"request": request, "post": saved_post, "draft": post_is_draft, "user": user},
    )


@admin_router.post("/post/{post_id}", response_class=HTMLResponse)
async def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    body: str = Form(...),
    tags: str = Form(""),
    difficulty: int = Form(0),
    draft: str = Form(None),
    user: dict = Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user
    post = blog_service.get_post_by_id(post_id, db)
    post.title = title
    post.body = body
    post.tags = [tag.strip() for tag in tags.split("\n") if tag.strip()]
    post.difficulty = difficulty
    post_is_draft = draft is not None

    if post_is_draft:
        # Using a far-future date for drafts
        if not post.published or post.published < datetime.datetime.now(
            datetime.timezone.utc
        ):
            post.published = datetime.datetime(9999, 12, 31)
    else:
        if not post.published or post.published.year == 9999:
            post.published = datetime.datetime.now(datetime.timezone.utc)
        post.updated = datetime.datetime.now(datetime.timezone.utc)

    saved_post = blog_service.save_post(post, db)
    return templates.TemplateResponse(
        "admin/published.html",
        {"request": request, "post": saved_post, "draft": post_is_draft, "user": user},
    )


@admin_router.post("/post/delete/{post_id}", response_class=HTMLResponse)
async def delete_post(
    request: Request,
    post_id: int,
    user: dict = Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user
    blog_service.delete_post(post_id, db)
    return templates.TemplateResponse(
        "admin/deleted.html", {"request": request, "user": user}
    )
