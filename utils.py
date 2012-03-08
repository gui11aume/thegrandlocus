import os
import re
import unicodedata

from google.appengine.ext import webapp
from google.appengine.ext.webapp.template import _swap_settings

import django.conf
from django import template
from django.template import loader

import config

BASE_DIR = os.path.dirname(__file__)

if isinstance(config.theme, (list, tuple)):
   # If speicified as a list/tuple in config, keep as is.
   TEMPLATE_DIRS = config.theme
else:
   # Else make a list with the specified theme and "default".
   TEMPLATE_DIRS = [os.path.abspath(os.path.join(BASE_DIR, 'themes/default'))]
   if config.theme and config.theme != 'default':
      TEMPLATE_DIRS.insert(0, os.path.abspath(os.path.join(
          BASE_DIR, 'themes', config.theme)
      ))


def slugify(s):
   """Slugify a string 's' (replace non letters and numbers by -)."""
   # s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
   # return re.sub('[^a-zA-Z0-9-]+', '-', s).strip('-')
   s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').lower()
   return re.sub('[^a-z0-9-]+', '-', s).strip('-')


def format_post_path(post, num):
   """Make the address of the post. Most of the action happens in
   'config', where a pre-formatted string is defined."""
   slug = slugify(post.title)
   if num > 0:
      slug += "-" + str(num)
   date = post.published_tz
   return config.post_path_format % {
       'slug': slug,
       'year': date.year,
       'month': date.month,
       'day': date.day,
   }


def get_template_vals_defaults(template_vals=None):
   """Add 2 pairs to the 'template_vals' dictionary: the config
   module and 'True' if SERVER_SOFTWARE starts with "Devel"."""
   if template_vals is None:
      template_vals = {}
   template_vals.update({
       'config': config,
       'devel': os.environ['SERVER_SOFTWARE'].startswith('Devel'),
   })
   return template_vals


def render_template(template_name, template_vals=None, theme=None):
   # Add 'config' and 'devel' to dictionary 'template_vals'.
   template_vals = get_template_vals_defaults(template_vals)
   # Add 'template_name'.
   template_vals.update({'template_name': template_name})
   # Set 'TEMPLATE_DIRS' in 'django.conf.settings' to the list of
   # template directories 'TEMPLATE_DIRS'.
   old_settings = _swap_settings({'TEMPLATE_DIRS': TEMPLATE_DIRS})
   try:
      # Make a 'Template' object from file and render it.
      tpl = loader.get_template(template_name)
      rendered = tpl.render(template.Context(template_vals))
   finally:
      # Leave 'django.conf.settings' as they were.
      _swap_settings(old_settings)
   return rendered


def _get_all_paths():
  import static
  keys = []
  q = static.StaticContent.all(keys_only=True).filter('indexed', True)
  cur = q.fetch(1000)
  while len(cur) == 1000:
    keys.extend(cur)
    q = static.StaticContent.all(keys_only=True)
    q.filter('indexed', True)
    q.filter('__key__ >', cur[-1])
    cur = q.fetch(1000)
  keys.extend(cur)
  return [x.name() for x in keys]


def _regenerate_sitemap():
  import static
  import gzip
  from StringIO import StringIO
  paths = _get_all_paths()
  rendered = render_template('sitemap.xml', {'paths': paths})
  static.set('/sitemap.xml', rendered, 'application/xml', False)
  s = StringIO()
  gzip.GzipFile(fileobj=s,mode='wb').write(rendered)
  s.seek(0)
  renderedgz = s.read()
  static.set('/sitemap.xml.gz',renderedgz, 'application/x-gzip', False)
  if config.google_sitemap_ping:
      ping_googlesitemap()

def ping_googlesitemap():
   import urllib
   from google.appengine.api import urlfetch
   google_url = 'http://www.google.com/webmasters/tools/ping?' \
      + 'sitemap=http://' + config.host + '/sitemap.xml.gz'
   response = urlfetch.fetch(google_url, '', urlfetch.GET)
   if response.status_code / 100 != 2:
      raise Warning(
          "Google Sitemap ping failed",
          response.status_code,
          response.content
      )

def tzinfo():
  """
  Returns an instance of a tzinfo implementation, as specified in
  config.tzinfo_class; else, None.
  """

  # None is defined in The Grand Locus config file.
  if not config.__dict__.get('tzinfo_class'):
    return None

  str = config.tzinfo_class
  i = str.rfind(".")

  try:
    # from str[:i] import str[i+1:]
    klass_str = str[i+1:]
    mod = __import__(str[:i], globals(), locals(), [klass_str])
    klass = getattr(mod, klass_str)
    return klass()
  except ImportError:
    return None

def tz_field(property):
  """
  For a DateTime property, make it timezone-aware if possible.

  If it already is timezone-aware, don't do anything.
  """
  if property.tzinfo:
    return property

  tz = tzinfo()
  if tz:
    # Nope... not in The Grand Locus, so we just return 'property'.
    # delay importing, hopefully after fix_path is done
    from timezones.utc import UTC

    return property.replace(tzinfo=UTC()).astimezone(tz)
  else:
    return property
