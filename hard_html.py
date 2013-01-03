# -*- coding: utf-8 -*-
#import setup_django_version

import os

import webapp2
#from google.appengine.ext import webapp
#from google.appengine.ext.webapp.util import run_wsgi_app

import utils

class HardHTMLServer(webapp.RequestHandler):
   """Server for 'hard' HTML files. Provides only Django templating.
   All hard HTML files have to be in the right theme directory."""

   def get(self, path):
      self.response.out.write(utils.render_template(path))



app = webapp2.WSGIApplication([
  ('/(.*html)', HardHTMLServer),
])
