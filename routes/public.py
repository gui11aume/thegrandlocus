from itertools import groupby

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from google.cloud import datastore

from config import settings
from services import blog as blog_service
from services.datastore import get_datastore_client

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/bestof")
def bestof(request: Request):
    return templates.TemplateResponse(
        request,
        "bestof.html",
        {
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )


@router.get("/archive")
def archive(request: Request, db: datastore.Client = Depends(get_datastore_client)):
    posts = blog_service.get_posts(db, limit=None)

    # Sort posts by year in descending order
    posts.sort(key=lambda p: p.published.year, reverse=True)

    # Group posts by year
    posts_by_year = []
    for _year, group in groupby(posts, key=lambda p: p.published.year):
        posts_by_year.append(list(group))

    return templates.TemplateResponse(
        request,
        "archive.html",
        {
            "settings": settings,
            "by_year": posts_by_year,
            "copyright_year": settings.copyright_year,
        },
    )


@router.get("/about")
def about(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {
            "settings": settings,
            "copyright_year": settings.copyright_year,
        },
    )
