# -*- coding: utf-8 -*-

import os
import sys
import datetime
import hashlib

import webapp2

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.datastore import entity_pb
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import blobstore_handlers

import blobmodels
import config
import utils

# Imports from the 'lib' directory.
import addlib
import aetycoon


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"
ROOT_ONLY_FILES = ['/robots.txt']


class StaticContent(db.Model):
   """Container for statically served content.
   The serving path for content is provided in the key name.
   """

   body = db.BlobProperty()
   content_type = db.StringProperty()
   status = db.IntegerProperty(required=True, default=200)
   last_modified = db.DateTimeProperty(required=True)
   # Instances of 'DerivedProperty' are generated when required,
   # this allows to filter or sort. Here that's the SHA1 of the body.
   etag = aetycoon.DerivedProperty(
       lambda x: hashlib.sha1(x.body).hexdigest()
   )
   indexed = db.BooleanProperty(required=True, default=True)
   headers = db.StringListProperty()


def get(path):
   """Return the StaticContent object for the given path.
   Args:
     path: The path to get the content from.
   Return:
     A StaticContent object or None.
   """

   # Nick Johnson explains the logic of the code here:
   # http://blog.notdot.net/2009/9/Efficient-model-memcaching
   # Using Protocol Buffers is way faster and more efficient than
   # pickling.

   # Addresses are case-insensitive.
   path = path.lower()

   # Try to retrieve the content from memcache.
   entity = memcache.get(path)
   if entity is not None:
      # Yeah, it was there. Decode it.
      entity = db.model_from_protobuf(entity_pb.EntityProto(entity))
   else:
      # Bad luck. Have to get that entity from its key (the path).
      entity = StaticContent.get_by_key_name(path)
      if entity is not None:
         # Now store it for next time, after encoding.
         memcache.set(path, db.model_to_protobuf(entity).Encode())

   return entity


def set(path, body, content_type, indexed=True, **kwargs):
   """Set the StaticContent for the provided path, save it
   to the datastore (with key as path), and save it in memcache.
   Args:
     path: The path to store the content against.
     body: The data to serve for that path.
     content_type: The MIME type to serve the content as.
     indexed: Index this page in the sitemap?
     **kwargs: Additional arguments to be passed to the StaticContent
       constructor
   Return:
     A StaticContent.
   """

   # Always convert 'path' to lower-case in order to make addresses
   # case-insensitive.
   path = path.lower()

   # Set extra arguments for the StaticContent constructor,
   # including the 'last_modified' attribute. Mostly there is
   # only space left for 'status' and 'headers'.
   now = datetime.datetime.now().replace(second=0, microsecond=0)
   defaults = { "last_modified": now }
   defaults.update(kwargs)
   try:
      body = unicode(body).encode('utf-8')
   except Exception, e:
      pass

   # Instantiate the 'StaticContent' object.
   content = StaticContent(
       key_name = path,
       body = body,
       content_type = content_type,
       indexed = indexed,
       **defaults
   )

   # Save it to the datastore and in memcache.
   content.put()
   memcache.replace(path, db.model_to_protobuf(content).Encode())

   try:
      # ETA of about 1 min from now.
      eta = now.replace(second=0, microsecond=0) + \
            datetime.timedelta(seconds=65)
      # If the content should be indexed in the site map
      # regenerate it... but later.
      if indexed:
        deferred.defer(
            utils._regenerate_sitemap,
            _name = 'sitemap-%s' % (now.strftime('%Y%m%d%H%M'),),
            _eta = eta
        )
   except ( taskqueue.taskqueue.TaskAlreadyExistsError,
            taskqueue.taskqueue.TombstonedTaskError     ), e:
      pass

   return content


def add(path, body, content_type, indexed=True, **kwargs):
   """Add a new StaticContent and return it.
   Args:
     As per set().
   Return:
     A StaticContent object, or None if one already exists
     at the given path.
   """

   def _tx():
      """The transaction: set the static content if 'path' does
      not exist, otherwise return None."""

      if StaticContent.get_by_key_name(path):
         return None
      return set(path, body, content_type, indexed, **kwargs)

   # Use 'db.run_in_transaction' to ensure that changes are atomic.
   # Either the static content is added, or nothing happens.
   return db.run_in_transaction(_tx)


def remove(path):
   """Delete a StaticContent.
   Args:
     path: Path of the static content to be removed.
   """

   # Remove from memcache.
   memcache.delete(path)

   def _tx():
      """The transaction: delete static content from datastore."""
      content = StaticContent.get_by_key_name(path)
      if not content:
         return
      content.delete()

   # Use 'db.run_in_transaction' to ensure that changes are atomic.
   # Either the static content is deleted, or nothing happens.
   return db.run_in_transaction(_tx)


class StaticContentHandler(webapp2.RequestHandler):
   """Handle all the requests for static content."""

   def output_content(self, content, serve=True):
      """Send the HTTP response, possibly without a content if the
      client used 'If-None-Match' or 'If-Modified-Since' headers."""

      # Prepare the headers.
      if content.content_type:
         self.response.headers['Content-Type'] = str(content.content_type)
      last_modified = content.last_modified.strftime(HTTP_DATE_FMT)
      self.response.headers['Last-Modified'] = str(last_modified)
      self.response.headers['ETag'] = str('"%s"' % content.etag)
      for header in content.headers:
         key, value = header.split(':', 1)
         self.response.headers[key] = str(value.strip())

      if serve:
         # Send headers, status and body.
         self.response.set_status(content.status)
         self.response.out.write(content.body)
      else:
         # Send a 304 (Not Modified) response without a body.
         self.response.set_status(304)

   def get(self, path):
      """Handle GET request on static blog content. Only get the
      static content and pass it to 'output_content'."""

      if not path.startswith(config.url_prefix):
         # Query does not start with prefix. It is OK if it should
         # be so, like for robots, else that's a 404 error.
         if path not in ROOT_ONLY_FILES:
            self.error(404)
            self.response.out.write(utils.render_template('404.html'))
            return
      else:
         # Query starts with prefix.
         if config.url_prefix != '':
            # Strip it off.
            path = path[len(config.url_prefix):]
            if path in ROOT_ONLY_FILES: # This lives at root
               self.error(404)
               self.response.out.write(utils.render_template('404.html'))
               return

      # Retrive the 'StaticContent' object from datastore or memcache.
      content = get(path)
      if not content:
         self.error(404)
         self.response.out.write(utils.render_template('404.html'))
         return

      # Ready to serve...
      serve = True

      # ... but first check If-Modified-Since and If-None-Match HTTP
      # headers (that are used for serving only if content has changed).
      if 'If-Modified-Since' in self.request.headers:
         try:
            last_seen = datetime.datetime.strptime(
                # IE8 '; length=XXXX' as extra arg bug
                self.request.headers['If-Modified-Since'].split(';')[0],
                HTTP_DATE_FMT
            )
            if last_seen >= content.last_modified.replace(microsecond=0):
               serve = False
         except ValueError, e:
            import logging
            logging.error(
                'StaticContentHandler in static.py, ValueError: ' + \
                self.request.headers['If-Modified-Since']
            )

      if 'If-None-Match' in self.request.headers:
        etags = [
            x.strip('" ')
            for x in self.request.headers['If-None-Match'].split(',')
        ]
        if content.etag in etags:
          serve = False

      self.output_content(content, serve)


class ImgHandler(blobstore_handlers.BlobstoreDownloadHandler):
   """HTML img tags are handled by the blobstore."""
   def get(self, path):
      img = blobmodels.BlobImage.get_by_key_name(path)
      self.send_blob(img.ref)


class AboutHandler(webapp2.RequestHandler):
   """HTML img tags are handled by the blobstore."""
   def get(self):
      self.response.out.write(utils.render_template("about.html"))


app = webapp2.WSGIApplication([
                ('/about.*', AboutHandler),
                ('/img/([^/]+)?', ImgHandler),
                ('(/.*)', StaticContentHandler),
              ])
