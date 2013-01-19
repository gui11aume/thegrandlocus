# -*- coding:utf-8 -*-

import datetime
import hashlib
import re

from google.appengine.ext import db
from google.appengine.ext import deferred

import config
import generators
import markup
import static
import utils

# Imports from the lib directory.
import addlib
import aetycoon

if config.default_markup in markup.MARKUP_MAP:
  DEFAULT_MARKUP = config.default_markup
else:
  DEFAULT_MARKUP = 'markdown'


class BlogDate(db.Model):
  """Contains a list of year-months for published blog posts."""

  @classmethod
  def get_key_name(cls, post):
    return '%d/%02d' % (post.published_tz.year, post.published_tz.month)

  @classmethod
  def create_for_post(cls, post):
    inst = BlogDate(key_name=BlogDate.get_key_name(post))
    inst.put()
    return inst

  @classmethod
  def datetime_from_key_name(cls, key_name):
    year, month = key_name.split("/")
    return datetime.datetime(int(year), int(month),
          1, tzinfo=utils.tzinfo())

  @property
  def date(self):
    return BlogDate.datetime_from_key_name(self.key().name()).date()

class FeedEntry(db.Model):
  """Entry model for Atom/RSS feeds.

  From October 2012, the feed entries are stored separately,
  and are updated only when the post is created. This way the
  feed will not be updated when the posts are edited and when
  maintenance is performed on the blog."""

  title = db.StringProperty(required=True, indexed=False)
  postpath = db.StringProperty()
  body = db.TextProperty(required=True)
  published = db.DateTimeProperty(auto_now_add=True)

  @property
  def published_tz(self):
    return utils.tz_field(self.published)

  @property
  def hash(self):
    val = (self.title, self.published)
    return hashlib.sha1(str(val)).hexdigest()

class BlogPost(db.Model):
  # The URL path to the blog post. Posts have a path iff they are published.
  path = db.StringProperty()
  title = db.StringProperty(required=True, indexed=False)
  body_markup = db.StringProperty(
                    choices = set(markup.MARKUP_MAP),
                    default = DEFAULT_MARKUP
                )
  body = db.TextProperty(required=True)
  tags = aetycoon.SetProperty(basestring, indexed=False)
  published = db.DateTimeProperty()
  updated = db.DateTimeProperty(auto_now=False)
  deps = aetycoon.PickleProperty()

  @property
  def published_tz(self):
    # Returns 'self.published' in The Grand Locus.
    return utils.tz_field(self.published)

  @property
  def updated_tz(self):
    # Same as above, returns 'self.published' in The Grand Locus.
    return utils.tz_field(self.updated)

  @aetycoon.TransformProperty(tags)
  def normalized_tags(tags):
    return list(set(utils.slugify(x.lower()) for x in tags))

  @property
  def tag_pairs(self):
    return [(x, utils.slugify(x.lower())) for x in self.tags]

  @property
  def rendered(self):
    """Returns the rendered body."""
    return markup.render_body(self)

  @property
  def summary(self):
    """Returns a summary of the blog post."""
    return markup.render_summary(self)

  @property
  def hash(self):
    val = (self.title, self.body, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  @property
  def summary_hash(self):
    val = (self.title, self.summary, self.tags, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  def publish(self):
    """Method called to publish or edit (non draft) posts.
    Give post a path if required and checks/regenerate
    dependencies."""

    regenerate = False

    if not self.path:
      # Post does not have a path (first time published).
      # Need to get one.
      num = 0
      content = None
      while not content:
        # Append incremental counter to path until a non used
        # path is found.
        path = utils.format_post_path(self, num)
        # 'static.add' returns 'None' if path is already in use.
        content = static.add(path, '', config.html_mime_type)
        num += 1
      self.path = path
      self.put()

      # Force regenerate on new publish. Also helps with generation of
      # chronologically previous and next page.
      regenerate = True

    # Post has a path, save post date in 'BlogDate' model.
    BlogDate.create_for_post(self)

    # Run through the deps, generate now what must be generated now,
    # defer the rest and save post to datastore (again).
    for generator_class, deps in self.get_deps(regenerate=regenerate):
      for dep in deps:
        if generator_class.can_defer:
          deferred.defer(generator_class.generate_resource, None, dep)
        else:
          generator_class.generate_resource(self, dep)
    self.put()


  def remove(self):
    if not self.is_saved():
      return
    # It is important that 'get_deps()' return the post dependency
    # before the list dependencies as the BlogPost entity gets deleted
    # while calling PostContentGenerator.
    for generator_class, deps in self.get_deps(regenerate=True):
      for dep in deps:
        if generator_class.can_defer:
          deferred.defer(generator_class.generate_resource, None, dep)
        else:
          if generator_class.name() == 'PostContentGenerator':
            generator_class.generate_resource(self, dep, action='delete')
            self.delete()
          else:
            generator_class.generate_resource(self, dep)

  def get_deps(self, regenerate=False):
    """Generator function of the dependencies of a post."""

    # 'deps' is a dictionary / 'aetycoon.PickleProperty' that
    # associates generator class name with a 2-tuple containing
    # the set of all dependencies for that class, and its etag.
    if not self.deps:
      self.deps = {}

    # 'generators.generator_list' contains classes of generators
    # that are required when (re)generating a post (PostContentGenerator,
    # PostPrevNextContentGenerator, IndexContentGenerator,
    # TagsContentGenerator, ArchivePageContentGenerator,
    # ArchiveIndexContentGenerator).
    for generator_class in generators.generator_list:
      # For each of those, get deps and etags.
      new_deps = set(generator_class.get_resource_list(self))
      new_etag = generator_class.get_etag(self)
      (old_deps, old_etag) = self.deps.get(
                               generator_class.name(),
                               # If undefined.
                               (set(), None)
                           )
      if new_etag != old_etag or regenerate:
        # If the etag has changed, regenerate everything
        to_regenerate = new_deps | old_deps
      else:
        # Otherwise just regenerate the changes
        to_regenerate = new_deps ^ old_deps
      self.deps[generator_class.name()] = (new_deps, new_etag)
      # Yield the generator class and the set of entities to
      # regenerate.
      yield generator_class, to_regenerate

class Page(db.Model):
  # The URL path to the page.
  path = db.StringProperty(required=True)
  title = db.TextProperty(required=True)
  template = db.StringProperty(required=True)
  body = db.TextProperty(required=True)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  updated = db.DateTimeProperty()

  @property
  def rendered(self):
    # Returns the rendered body.
    return markup.render_body(self)

  @property
  def hash(self):
    val = (self.path, self.body, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  def publish(self):
    self._key_name = self.path
    self.put()
    generators.PageContentGenerator.generate_resource(self, self.path);

  def remove(self):
    if not self.is_saved():
      return
    self.delete()
    generators.PageContentGenerator.generate_resource(self, self.path, action='delete')

#class VersionInfo(db.Model):
#  bloggart_major = db.IntegerProperty(required=True)
#  bloggart_minor = db.IntegerProperty(required=True)
#  bloggart_rev = db.IntegerProperty(required=True)
#
#  @property
#  def bloggart_version(self):
#    return (self.bloggart_major, self.bloggart_minor, self.bloggart_rev)
