#import setup_django_version

import os
import re
import unicodedata

import jinja2

import config

from HTMLEditor import URLAbsolutifier

# Globals.
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
JINJA_ENV = jinja2.Environment(
          loader=jinja2.FileSystemLoader(TEMPLATE_DIR))


def slugify(s):
   """Slugify a unicode string (replace non letters and numbers
   by "-")."""

   # Slug is lower case.
   s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
   return re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower()).strip("-")


def format_post_path(post, num):
   """Make the address of the post. Most of the action happens in
   'config', where a pre-formatted string is defined."""

   slug = slugify(post.title)
   # Do not append 0, only greater integers.
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
   """For every template to render, add 'config' and 'devel'."""

   if template_vals is None:
      template_vals = {}
   template_vals.update({
       'config': config,
       'devel': os.environ['SERVER_SOFTWARE'].startswith('Devel'),
   })
   return template_vals


def render_template(template_name, template_vals=None):
   template = JINJA_ENV.get_template(template_name)
   template_vals = get_template_vals_defaults(template_vals)
   template_vals.update({'template_name': template_name})
   return template.render(template_vals)


def _get_all_paths():
   """Well, this one gets all paths."""

   # Pages are stored as 'StaticContent' model objects (defined
   # in 'static') in the datastore.
   import static
   keys = []

   # Get all 'StaticContent' objects by key and keep only
   # the ones for which 'indexed' is set to True (the ones
   # to be indexed on the site map).
   q = static.StaticContent.all(keys_only=True).filter('indexed', True)

   # Fetch the first 1000 keys/paths.
   cur = q.fetch(1000)

   # If we don't have them all, process by batch of 1000.
   while len(cur) == 1000:
      # Add the batck to 'keys'.
      keys.extend(cur)
      q = static.StaticContent.all(keys_only=True)
      q.filter('indexed', True)
      # Query only those with key larger than the last stored
      # in 'keys'.
      q.filter('__key__ >', cur[-1])
      cur = q.fetch(1000)

   # Add to 'keys' whatever is left.
   keys.extend(cur)

   # Return the list of all key names, ie paths.
   return [x.name() for x in keys]


def _regenerate_sitemap():
   """Regenerate the site map (contains all the paths of the indexed
   static content), put it on /sitemap.xml and /sitemap.xml.gz and
   tell Google if required by 'config'."""

   import static
   import gzip
   from StringIO import StringIO

   # Get all indexed paths in the list 'paths'.
   paths = _get_all_paths()

   # Use the Django 'sitemap.xml' template and fill it with 
   # all indexed paths of the app.
   rendered = render_template(
        'sitemap.xml', {'paths': paths, 'host': config.host}
   )

   # Set the map as SataticContent at /sitemap.xml and don't index it
   # (to prevent entering an infinite loop).
   static.set('/sitemap.xml', rendered, 'application/xml', False)

   # Also gzip it, and set this at /sitemap.xml.gz.
   s = StringIO()
   gzip.GzipFile(fileobj=s, mode='wb').write(rendered)
   s.seek(0)
   rendrdgz = s.read()
   static.set('/sitemap.xml.gz', rendrdgz, 'application/x-gzip', False)

   # If required by 'config', tell Google where we put it.
   if config.google_sitemap_ping:
      ping_googlesitemap()


def ping_googlesitemap():
   """Send a GET to google with the address of our site map."""

   import urllib
   from google.appengine.api import urlfetch
   google_url = 'http://www.google.com/webmasters/tools/ping?' \
      + 'sitemap=http://' + config.host + '/sitemap.xml.gz'
   response = urlfetch.fetch(google_url, '', urlfetch.GET)

   # Does not return, but raise a warning if something goes wrong.
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
  """For a DateTime property, make it timezone-aware if possible.
  If it already is timezone-aware, don't do anything."""

  if property.tzinfo:
    return property

  tz = tzinfo()
  if tz:
    # Nope... not in The Grand Locus, so we just return 'property'.
    # delay importing, hopefully after fix_path is done
    import addlib
    from timezones.utc import UTC

    return property.replace(tzinfo=UTC()).astimezone(tz)
  else:
    return property


def absolutify_url(html):
   # Uses proper HTML parsing to make local URL absolutes.
   absolutifier = URLAbsolutifier(config.host)
   return absolutifier.process(html)
