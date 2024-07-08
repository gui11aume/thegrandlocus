# Standard library imports.
import datetime
import hashlib

# Google App Engine imports.
from google.appengine.ext import ndb
from google.cloud import datastore

datastore_client = datastore.Client()


class StaticContent(ndb.Model):
    """Container for statically served content.
    The serving path for content is provided in the key name.
    """

    body = ndb.BlobProperty()
    content_type = ndb.StringProperty()
    status = ndb.IntegerProperty(required=True, default=200)
    last_modified = ndb.DateTimeProperty(required=True)
    indexed = ndb.BooleanProperty(required=True, default=True)
    headers = ndb.StringProperty(repeated=True)
    etag = ndb.ComputedProperty(
       lambda self: hashlib.sha1(self.body).hexdigest()
    )

def set_content(path, body, content_type, indexed=True, **kwargs):
   key = ndb.Key("StaticContent", f"{path.lower()}")
   now = datetime.datetime.now().replace(second=0, microsecond=0)
   if isinstance(body, str):
      body = body.encode("utf-8")
   properties = {
        "key": key,
        "body": body,
        "content_type": content_type,
        "last_modified": now,
        "indexed": indexed,
   }
   properties.update(kwargs)
   entity = StaticContent(**properties)
   entity.put()
   return entity

   # Save it to the datastore and in memcache.
   # content.put()
   # memcache.replace(path, db.model_to_protobuf(content).Encode())

   # try:
   #    # ETA of about 1 min from now.
   #    eta = now.replace(second=0, microsecond=0) + \
   #          datetime.timedelta(seconds=65)
   #    # If the content should be indexed in the site map
   #    # regenerate it... but later.
   #    if indexed:
   #      deferred.defer(
   #          utils._regenerate_sitemap,
   #          _name = 'sitemap-%s' % (now.strftime('%Y%m%d%H%M'),),
   #          _eta = eta
   #      )
   # except ( taskqueue.taskqueue.TaskAlreadyExistsError,
   #          taskqueue.taskqueue.TombstonedTaskError     ):
   #    pass
   # 
   # return content

def remove_content(path):
   datastore_key = datastore_client.key("StaticContent", f"{path.lower()}")
   datastore_client.delete(datastore_key)
