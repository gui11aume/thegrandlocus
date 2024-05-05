import os
import sys
import datetime
import hashlib

import aetycoon
#import blobmodels
import models

from flask import Flask, abort, make_response, render_template, \
   request, session, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage import BaseStorage

from google.appengine.api import taskqueue
from google.appengine.api import wrap_wsgi_app
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext import deferred
from google.cloud import datastore


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

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
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
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

ds_client = datastore.Client()


class StaticContent(ndb.Model):
   """Container for statically served content.
   The serving path for content is provided in the key name.
   """

   body = ndb.BlobProperty()
   content_type = ndb.StringProperty()
   status = ndb.IntegerProperty(required=True, default=200)
   last_modified = ndb.DateTimeProperty(required=True)
   # Instances of 'DerivedProperty' are generated when required,
   # this allows to filter or sort. Here that's the SHA1 of the body.
   etag = aetycoon.DerivedProperty(
       lambda x: hashlib.sha1(x.body).hexdigest()
   )
   indexed = ndb.BooleanProperty(required=True, default=True)
   headers = ndb.StringProperty(repeated=True)



#def set(path, body, content_type, indexed=True, **kwargs):
#   """Set the StaticContent for the provided path, save it
#   to the datastore (with key as path), and save it in memcache.
#   Args:
#     path: The path to store the content against.
#     body: The data to serve for that path.
#     content_type: The MIME type to serve the content as.
#     indexed: Index this page in the sitemap?
#     **kwargs: Additional arguments to be passed to the StaticContent
#       constructor
#   Return:
#     A StaticContent.
#   """
#
#   # Always convert 'path' to lower-case in order to make addresses
#   # case-insensitive.
#   path = path.lower()
#
#   # Set extra arguments for the StaticContent constructor,
#   # including the 'last_modified' attribute. Mostly there is
#   # only space left for 'status' and 'headers'.
#   now = datetime.datetime.now().replace(second=0, microsecond=0)
#   defaults = { "last_modified": now }
#   defaults.update(kwargs)
#   try:
#      body = unicode(body).encode('utf-8')
#   except Exception, e:
#      pass
#
#   # Instantiate the 'StaticContent' object.
#   content = StaticContent(
#       key_name = path,
#       body = body,
#       content_type = content_type,
#       indexed = indexed,
#       **defaults
#   )
#
#   # Save it to the datastore and in memcache.
#   content.put()
#   memcache.replace(path, ndb.model_to_protobuf(content).Encode())
#
#   try:
#      # ETA of about 1 min from now.
#      eta = now.replace(second=0, microsecond=0) + \
#            datetime.timedelta(seconds=65)
#      # If the content should be indexed in the site map
#      # regenerate it... but later.
#      if indexed:
#        deferred.defer(
#            utils._regenerate_sitemap,
#            _name = 'sitemap-%s' % (now.strftime('%Y%m%d%H%M'),),
#            _eta = eta
#        )
#   except ( taskqueue.taskqueue.TaskAlreadyExistsError,
#            taskqueue.taskqueue.TombstonedTaskError     ), e:
#      pass
#
#   return content
#
#
#def add(path, body, content_type, indexed=True, **kwargs):
#   """Add a new StaticContent and return it.
#   Args:
#     As per set().
#   Return:
#     A StaticContent object, or None if one already exists
#     at the given path.
#   """
#
#   def _tx():
#      """The transaction: set the static content if 'path' does
#      not exist, otherwise return None."""
#
#      if StaticContent.get_by_key_name(path):
#         return None
#      return set(path, body, content_type, indexed, **kwargs)
#
#   # Use 'ndb.run_in_transaction' to ensure that changes are atomic.
#   # Either the static content is added, or nothing happens.
#   return ndb.run_in_transaction(_tx)
#
#
#def remove(path):
#   """Delete a StaticContent.
#   Args:
#     path: Path of the static content to be removed.
#   """
#
#   # Remove from memcache.
#   memcache.delete(path)
#
#   def _tx():
#      """The transaction: delete static content from datastore."""
#      content = StaticContent.get_by_key_name(path)
#      if not content:
#         return
#      content.delete()
#
#   # Use 'ndb.run_in_transaction' to ensure that changes are atomic.
#   # Either the static content is deleted, or nothing happens.
#   return ndb.run_in_transaction(_tx)



@app.errorhandler(404)
def not_found(arg):
    return make_response(render_template("404.html"), 404)


class ImgHandler(blobstore.BlobstoreDownloadHandler):
   """HTML img tags are handled by the blobstore."""
   def get(self, key):
      if not blobstore.get(key):
         return "Not found", 404
      else:
         headers = self.send_blob(request.environ, key)
         headers["Content-Type"] = None
         return "", headers

@app.route("/img/<path>")
def img(path):
   image = ds_client.get(ds_client.key("BlobImage", path))
   return ImgHandler().get(image["ref"])
   
   
@app.route("/admin/")
def admin():
   if not google.authorized:
      return redirect(url_for("google.login"))
   resp = google.get("/oauth2/v2/userinfo")
   assert resp.ok, resp.text
   if resp.json()["email"] != "guillaume.filion@gmail.com":
      return "Not authorized", 403
   offset = int(request.args.get('start', 0))
   count = int(request.args.get('count', 20))   
   posts = models.BlogPost.all().order('-published').fetch(count, offset)
   images = blobstore.BlobInfo.all().order('-creation').fetch(count, offset)
   template_vals = {
      'offset': offset,
      'count': count,
      'last_post': offset + len(posts) - 1,
      'prev_offset': max(0, offset - count),
      'next_offset': offset + count,
      'posts': posts,
      'images': images,
      'upload_url': blobstore.create_upload_url('/admin/upload'),
   }
   return render_template("index.html", **template_vals)

@app.route("/admin/<path:path>")
def broken(path):
   return render_template("about.html")
   # if path == "":
   #    #offset = int(self.request.get('start', 0))
   #    #count = int(self.request.get('count', 20))
   #    offset = 0
   #    count = 20
   #    posts = models.BlogPost.all().order('-published').fetch(count, offset)
   #    images = blobstore.BlobInfo.all().order('-creation').fetch(count, offset)
   #    template_vals = {
   #       'offset': offset,
   #       'count': count,
   #       'last_post': offset + len(posts) - 1,
   #       'prev_offset': max(0, offset - count),
   #       'next_offset': offset + count,
   #       'posts': posts,
   #       'images': images,
   #       'upload_url': blobstore.create_upload_url('/admin/upload'),
   #    }
   #    return render_template("index.html", template_vals)

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
   content = ds_client.get(ds_client.key("StaticContent", f"/{path.lower()}"))
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
