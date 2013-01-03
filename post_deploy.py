# -*- coding:utf-8 -*-

import os
import datetime
import logging
from google.appengine.api import taskqueue
from google.appengine.ext import deferred

import config
import models
import static
import utils
import generators

# Difficult to say which version is it now.
# This is the version I when I forked bloggart.
BLOGGART_VERSION = (1, 0, 1)


class PostRegenerator(object):
  def __init__(self):
    # 'seen' is a set of visited (entity class, entity) pairs.
    self.seen = set()

  def regenerate(self, batch_size=50, start_ts=None):
    # Query all posts, sort by decreasing published property.
    q = models.BlogPost.all().order('-published')
    # Query only the posts published before 'start_ts' if provided.
    q.filter('published <', start_ts or datetime.datetime.max)
    # Fetch them by 'batch_size' (defaults to 50).
    posts = q.fetch(batch_size)
    for post in posts:
      # Walk through the classes of dependencies and the entities
      # to regenerate (all of them because we force 'regenerate=True'.
      for generator_class, deps in post.get_deps(True):
        # 'deps' is a set of entites to regenerate.
        for dep in deps:
          if (generator_class.__name__, dep) not in self.seen:
            logging.warn((generator_class.__name__, dep))
            self.seen.add((generator_class.__name__, dep))
            deferred.defer(generator_class.generate_resource, None, dep)

      # Save changes.
      post.put()

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
      deferred.defer(generators.PageContentGenerator.generate_resource, page, None);
      page.put()
    if len(pages) == batch_size:
      deferred.defer(self.regenerate, batch_size, pages[-1].created)

post_deploy_tasks = []


def generate_static_pages(pages):
  def generate(previous_version):
    for path, template, indexed in pages:
      rendered = utils.render_template(template)
      static.set(path, rendered, config.html_mime_type, indexed)
  return generate

post_deploy_tasks.append(generate_static_pages([
#    ('/search', 'search.html', True),
#    ('/cse.xml', 'cse.xml', False),
    ('/robots.txt', 'robots.txt', False),
]))


def regenerate_all(previous_version):
  if (
    previous_version.bloggart_major,
    previous_version.bloggart_minor,
    previous_version.bloggart_rev,
  ) < BLOGGART_VERSION:
    regen = PostRegenerator()
    deferred.defer(regen.regenerate)

post_deploy_tasks.append(regenerate_all)


def site_verification(previous_version):
  static.set('/' + config.google_site_verif,
             utils.render_template('site_verification.html'),
             config.html_mime_type, False)


def run_deploy_task():
  """Attempts to run the per-version deploy task."""
  task_name = 'deploy-%s' % os.environ['CURRENT_VERSION_ID'].replace('.', '-')
  try:
    deferred.defer(try_post_deploy, _name=task_name, _countdown=10)
  except (taskqueue.TaskAlreadyExistsError, taskqueue.taskqueue.TombstonedTaskError), e:
    pass


def try_post_deploy(force=False):
  """
  Runs post_deploy() if it has not been run for this version yet.

  If force is True, run post_deploy() anyway, but don't create a new
  VersionInfo entity.
  """
  version_info = models.VersionInfo.get_by_key_name(
      os.environ['CURRENT_VERSION_ID'])
  if not version_info:
    q = models.VersionInfo.all()
    q.order('-bloggart_major')
    q.order('-bloggart_minor')
    q.order('-bloggart_rev')

    version_info = q.get()

    # This might be an initial deployment; create the first VersionInfo
    # entity.
    if not version_info:
      version_info = models.VersionInfo(
        key_name=os.environ['CURRENT_VERSION_ID'],
        bloggart_major = BLOGGART_VERSION[0],
        bloggart_minor = BLOGGART_VERSION[1],
        bloggart_rev = BLOGGART_VERSION[2])
      version_info.put()

      post_deploy(version_info, is_new=False)
    else:
      post_deploy(version_info)
  elif force: # also implies version_info is available
    post_deploy(version_info, is_new=False)

def post_deploy(previous_version, is_new=True):
  """Carries out post-deploy functions, such as rendering static pages.
  If is_new is true, a new VersionInfo entity will be created."""
  for task in post_deploy_tasks:
    task(previous_version)

  # don't proceed to create a VersionInfo entity
  if not is_new:
    return

  new_version = models.VersionInfo(
      key_name=os.environ['CURRENT_VERSION_ID'],
      bloggart_major = BLOGGART_VERSION[0],
      bloggart_minor = BLOGGART_VERSION[1],
      bloggart_rev = BLOGGART_VERSION[2])
  new_version.put()
