# -*- coding:utf-8 -*-

#import setup_django_version

from google.appengine.ext import db
from google.appengine.ext import blobstore

class BlobImage(db.Model):
   """Simple model for blob images. This allows to set the path of
   an image to '/img/image_name'."""

   ref = blobstore.BlobReferenceProperty(blobstore.BlobKey, required=True)
