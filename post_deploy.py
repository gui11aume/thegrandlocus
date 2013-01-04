# -*- coding:utf-8 -*-

import datetime
import logging
from google.appengine.ext import deferred

import config
import models
import static
import utils
import generators


class PostRegenerator(object):
  def __init__(self):
    # 'seen' is a set of visited (entity class, entity) pairs.
    self.seen = set()

  def regenerate(self, batch_size=50, start_ts=None):
    # Query all posts, sort by decreasing published property.
    q = models.BlogPost.all().order('-published')
    # Query only the posts published before 'start_ts' if provided.
    # Should exclude drafts, which have a published time in the
    # future.
    q.filter('published <', start_ts or datetime.datetime.now())
    # Fetch them by 'batch_size' (defaults to 50).
    posts = q.fetch(batch_size)
    for post in posts:
      # Walk through the classes of dependencies and the entities
      # to regenerate (all of them because we force 'regenerate=True'.
      for generator_class, deps in post.get_deps(True):
        # 'deps' is a set of entites to regenerate.
        for dep in deps:
          if (generator_class.__name__, dep) not in self.seen:
            # Generate a series of warning in the logs, just to
            # keep track of what has been regenerated.
            logging.warn((generator_class.__name__, dep))
            self.seen.add((generator_class.__name__, dep))
            deferred.defer(generator_class.generate_resource, None, dep)
    if len(posts) == batch_size:
      deferred.defer(self.regenerate, batch_size, posts[-1].published)


class PageRegenerator(object):
  def __init__(self):
    self.seen = set()

  def regenerate(self, batch_size=50, start_ts=None):
    q = models.Page.all().order('-created')
    q.filter('created <', start_ts or datetime.datetime.max)
    pages = q.fetch(batch_size)
    for page in pages:
      deferred.defer(generators.PageContentGenerator.generate_resource,
            page, None);
      #page.put()
    if len(pages) == batch_size:
      deferred.defer(self.regenerate, batch_size, pages[-1].created)

post_deploy_tasks = []


def generate_static_pages(pages):
  def generate():
    for path, template, indexed in pages:
      rendered = utils.render_template(template)
      static.set(path, rendered, config.html_mime_type, indexed)
  return generate

post_deploy_tasks.append(generate_static_pages([
#    ('/search', 'search.html', True),
#    ('/cse.xml', 'cse.xml', False),
    ('/robots.txt', 'robots.txt', False),
]))


def regenerate_all():
    regen = PostRegenerator()
    deferred.defer(regen.regenerate)

post_deploy_tasks.append(regenerate_all)

def post_deploy():
   for task in post_deploy_tasks:
      task()
