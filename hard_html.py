# -*- coding: utf-8 -*-
import setup_django_version

import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import utils

class HardHTMLServer(webapp.RequestHandler):
   """Server for 'hard' HTML files. Provides only Django templating.
   All hard HTML files have to be in the right theme directory."""

   def get(self, path):
      self.response.out.write(utils.render_template(path))
      


application = webapp.WSGIApplication([
  ('/(.*html)', HardHTMLServer),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
