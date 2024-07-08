import datetime
import hashlib
import mimetypes

import aetycoon
import config
import models

from flask import Flask, Response, abort, make_response, render_template, \
   request, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage import BaseStorage

#from google.appengine.api import taskqueue
from google.appengine.api import wrap_wsgi_app
from google.appengine.ext import blobstore
#from google.appengine.ext import deferred
from google.cloud import datastore
from google.cloud import storage

from werkzeug.utils import secure_filename

import logging
logging.basicConfig(level=logging.INFO)


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

storage_client = storage.Client()
datastore_client = datastore.Client()

class MemoryStorage(BaseStorage):
    def __init__(self):
        self.token = None
    def get(self, blueprint):
        return self.token
    def set(self, blueprint, token):
        self.token = token
    def delete(self, blueprint):
        self.token = None

google_blueprint = make_google_blueprint(
#    client_id=os.getenv("GOOGLE_CLIENT_ID"),
#    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ],
    storage=MemoryStorage()
)


app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app, use_deferred=True)
app.register_blueprint(google_blueprint, url_prefix="/login")


def post_by_id(post_id):
   """Retrieve a `BlogPost` object from its id."""
   if post_id is None:
      return None
   post = models.BlogPost.get_by_id(int(post_id))
   if not post:
      abort(404)
   return post



@app.errorhandler(404)
def not_found(arg):
   return make_response(render_template("404.html"), 404)


@app.route("/img/<path:path>")
def img(path):
   # image = ds_client.get(ds_client.key("BlobImage", path))
   # return ImgHandler().get(image["ref"])
   bucket = storage_client.bucket("thegrandlocus_bucket")
   blob = bucket.blob(path)
   if not blob.exists():
      return "Not found", 404
   else:
      blob_data = blob.download_as_bytes()
      mime_type, _ = mimetypes.guess_type(blob.name)
      if mime_type is None:
         mime_type = "application/octet-stream"
      return Response(blob_data, mimetype=mime_type)


#    (config.url_prefix + '/admin/regenerate', handlers.RegenerateHandler),
# #  (config.url_prefix + '/admin/post/preview/(\d+)', handlers.PreviewHandler),
#    (config.url_prefix + '/preview/(\d+)', handlers.PreviewHandler),
#    (config.url_prefix + '/admin/delete/(.*)', handlers.DeleteImgHandler),
#], debug=True)

@app.route("/admin/")
def admin():
   # Check that it's me.
   if not google.authorized:
      return redirect(url_for("google.login"))
   resp = google.get("/oauth2/v2/userinfo")
   assert resp.ok, resp.text
   if resp.json()["email"] != "guillaume.filion@gmail.com":
      return "Not authorized", 403
   # Serve main page.
   offset = int(request.args.get('start', 0))
   count = int(request.args.get('count', 20))
   # TODO: Move to the Firestore. <===========================================
   posts = models.BlogPost.all().order('-published').fetch(count, offset)
   template_vals = {
      'offset': offset,
      'count': count,
      'last_post': offset + len(posts) - 1,
      'prev_offset': max(0, offset - count),
      'next_offset': offset + count,
      'posts': posts,
   }
   return render_template("index.html", **template_vals)

@app.route("/admin/newpost/", defaults={"post_id": None}, methods=["GET", "POST"])
@app.route("/admin/post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
   # Check that it's me.
   if not google.authorized:
      return redirect(url_for("google.login"))
   resp = google.get("/oauth2/v2/userinfo")
   assert resp.ok, resp.text
   if resp.json()["email"] != "guillaume.filion@gmail.com":
      return "Not authorized", 403
   
   # Handle GET (edit blog post).
   if request.method == "GET":
      return render_template("edit.html", post=post_by_id(post_id))
   
   # Handle POST (save blog post).
   if request.method == "POST":
      post_is_draft = request.form.get("draft")
      title = request.form.get("title", "no title")
      body = request.form.get("body", "no body")
      post = post_by_id(post_id)
      if post is None:
         post = models.BlogPost(
               title = title,
               body = body
         )
      else:
         post.title = title
         post.body = body
      # TODO: everything is markdown.
      post.body_markup = "markdown"
      post.tags = set([
            tag.strip()
            for tag in request.form.get('tags').split('\n')
      ])
      post.difficulty = int(request.form.get('difficulty', 0))

      if post_is_draft:
         # Post is a draft. Save, do not publish.
         if not post.path: post.published = datetime.datetime.max
         post.put()
      else:
         if post.path:
            # Post had a path: edit.
            post.updated = datetime.datetime.now()
         else:
            # Post had no path (new post): publish.
            post.updated = post.published = datetime.datetime.now()
         # Give post a path, update dependencies and dates.
         # No need to call 'post.put()' because 'post.publish()' takes
         # care of this.
         post.publish()

      return render_template("published.html", draft=post_is_draft, post=post)


@app.route("/admin/post/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
   post = post_by_id(post_id)
   if post is None:
      redirect(url_for("admin"))
   if post.path: # Published post
      post.remove()
   else:# Draft
      post.delete()
   return render_template("deleted.html")


@app.route("/preview/<int:post_id>")
def preview(post_id):
   post = post_by_id(post_id)
   if post is None:
      abort(404)
   if post.published == datetime.datetime.max:
      post.published = datetime.datetime.now()
   return render_template("post-preview.html",
      post=post,
      date_format=config.date_format
   )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def main(path):
   # Pure HTML page.
   if path == "about":
      return render_template("about.html")
   if path == "bestof":
      return render_template("bestof.html")
   if path == "robots.txt":
      return render_template("robots.txt")
   # Retrieve from static pages.
   datastore_key = datastore_client.key("StaticContent", f"/{path.lower()}")
   content = datastore_client.get(datastore_key)
   if not content:
      abort(404)
   headers = {
       "Content-Type": content["content_type"],
       "Last-Modified": content["last_modified"].strftime(HTTP_DATE_FMT),
       "ETag": '"' + content["etag"] + '"'
   }
   return content["body"], 200, headers


if __name__ == "__main__":
   app.run(host="127.0.0.1", port=8080, debug=True)
