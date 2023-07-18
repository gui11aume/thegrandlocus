from google.appengine.ext import ndb
from google.appengine.ext import blobstore

class BlobImage(ndb.Model):
   """Simple model for blob images. This allows to set the path of
   an image to '/img/image_name'."""

   ref = blobstore.BlobReferenceProperty(blobstore.BlobKey, required=True)
