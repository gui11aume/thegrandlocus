import mimetypes
from fastapi import FastAPI, Response, Request, Depends, HTTPException
from google.cloud import storage, datastore
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from routes.admin_fastapi import admin_router
from routes.public import router as public_router
from services import blog as blog_service
from services.google_auth import oauth
from services.datastore import get_datastore_client
from config import settings
from schemas import PostList, PostDetails, PostSummary

app = FastAPI()

# Add middleware for proxy headers and sessions
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
SECRET_KEY = settings.secret_key
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(admin_router, prefix="/admin")
app.include_router(public_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_storage_client():
    return storage.Client()


@app.get("/", response_class=templates.TemplateResponse)
def read_root(request: Request, db: datastore.Client = Depends(get_datastore_client)):
    posts = blog_service.get_posts(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "posts": posts,
            "settings": settings,
            "prev_page": None,
            "next_page": None,
            "copyright_year": settings.copyright_year,
            "generator_class": "IndexContentGenerator",
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
def get_image(
    image_path: str, storage_client: storage.Client = Depends(get_storage_client)
):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    if user:
        request.session["user"] = dict(user)
    return RedirectResponse(url="/admin/")


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@app.get("/preview/{post_id}")
def preview_post(
    request: Request,
    post_id: int,
    db: datastore.Client = Depends(get_datastore_client),
):
    post = blog_service.get_post_by_id(post_id, db)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "post.html",
        {
            "request": request,
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
    path = f"/{year}/{month:02d}/{slug}"
    post = blog_service.get_post_by_path(path, db)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "post.html",
        {
            "request": request,
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
        "listing.html",
        {
            "request": request,
            "posts": posts,
            "title": f"Posts tagged with '{tag}'",
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )
