import logging
import mimetypes

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import datastore, storage
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from config import settings
from routes.admin_fastapi import admin_router, get_current_user
from routes.public import router as public_router
from schemas import PostDetails, PostList, PostSummary
from security import (
    is_production_runtime,
    oauth_email_allowed,
    trusted_proxy_hosts_from_setting,
    validate_image_blob_path,
)
from services import blog as blog_service
from services.datastore import get_datastore_client
from services.google_auth import oauth

logger = logging.getLogger(__name__)

# Stdout is always ingested by Cloud Logging; `logger.info` is often dropped (root level WARNING).
print(f"services.blog loaded from {blog_service.__file__}", flush=True)

app = FastAPI()

# Add middleware for proxy headers and sessions.
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=trusted_proxy_hosts_from_setting(settings.trusted_proxy_hosts),
)
SECRET_KEY = settings.secret_key
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=is_production_runtime(),
)

app.include_router(admin_router, prefix="/admin")
app.include_router(public_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_storage_client():
    return storage.Client()


@app.get("/", response_class=HTMLResponse)
def read_root(
    request: Request,
    start: int = 0,
    db: datastore.Client = Depends(get_datastore_client),
):
    posts, total_posts = blog_service.get_posts(
        db, offset=start, limit=settings.posts_per_page, with_total=True
    )

    next_page_start = start + settings.posts_per_page
    if next_page_start < total_posts:
        next_page = f"/?start={next_page_start}"
    else:
        next_page = None

    if start > 0:
        prev_page_start = start - settings.posts_per_page
        if prev_page_start <= 0:
            prev_page = "/"
        else:
            prev_page = f"/?start={prev_page_start}"

    else:
        prev_page = None

    return templates.TemplateResponse(
        request,
        "listing.html",
        {
            "posts": posts,
            "settings": settings,
            "prev_page": prev_page,
            "next_page": next_page,
            "copyright_year": settings.copyright_year,
        },
    )


@app.get("/posts", response_model=PostList)
def list_posts_api(db: datastore.Client = Depends(get_datastore_client)):
    posts = blog_service.get_posts(db)
    results = [
        PostSummary(
            key=post.key.id_or_name,
            title=post.title,
            published=post.published,
            path=post.path,
        )
        for post in posts
    ]
    return {"posts": results}


@app.get("/posts/{post_id}", response_model=PostDetails)
def get_post(post_id: str, db: datastore.Client = Depends(get_datastore_client)):
    try:
        post_key_id = int(post_id)
        post = blog_service.get_post_by_id(post_key_id, db)
    except ValueError:
        post = blog_service.get_post_by_path(f"/posts/{post_id}", db)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not blog_service.is_post_visible_to_public(post):
        raise HTTPException(status_code=404, detail="Post not found")

    return PostDetails(
        key=post.key.id_or_name,
        title=post.title,
        body=post.body,
        published=post.published,
        updated=post.updated,
        path=post.path,
        tags=post.tags,
    )


@app.get("/img/{image_path:path}")
def get_image(image_path: str, storage_client: storage.Client = Depends(get_storage_client)):
    validate_image_blob_path(image_path)
    bucket = storage_client.bucket("thegrandlocus_bucket")
    blob = bucket.blob(image_path)

    if not blob.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        image_data = blob.download_as_bytes()
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
        return Response(content=image_data, media_type=mime_type)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to serve image from storage")
        raise HTTPException(status_code=500, detail="Could not load image") from None


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    if not user:
        return RedirectResponse(url="/login?error=no_userinfo", status_code=303)
    email = user.get("email")
    if not oauth_email_allowed(email, settings.admin_emails):
        return RedirectResponse(url="/login?error=forbidden", status_code=303)
    request.session["user"] = dict(user)
    return RedirectResponse(url="/admin/")


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@app.get("/preview/{post_id}")
async def preview_post(
    request: Request,
    post_id: int,
    user=Depends(get_current_user),
    db: datastore.Client = Depends(get_datastore_client),
):
    if isinstance(user, RedirectResponse):
        return user
    post = blog_service.get_post_by_id(post_id, db)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        request,
        "post.html",
        {
            "post": post,
            "path": post.path,
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )


@app.get("/{year:int}/{month:int}/{slug}")
def get_post_by_path(
    request: Request,
    year: int,
    month: int,
    slug: str,
    db: datastore.Client = Depends(get_datastore_client),
):
    path = f"/{year}/{month:02d}/{slug.lower()}"
    post = blog_service.get_post_by_path(path, db)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not blog_service.is_post_visible_to_public(post):
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        request,
        "post.html",
        {
            "post": post,
            "path": post.path,
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )


@app.get("/tag/{tag}")
def get_posts_by_tag(
    request: Request, tag: str, db: datastore.Client = Depends(get_datastore_client)
):
    posts = blog_service.get_posts_by_tag(tag, db)
    return templates.TemplateResponse(
        request,
        "listing.html",
        {
            "posts": posts,
            "title": f"Posts tagged with '{tag}'",
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/images/favicon.ico")
