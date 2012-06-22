import setup_django_version

import datetime
import logging
import os
import re

from google.appengine.ext import blobstore
from google.appengine.ext import deferred
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers

import config
import markup
import models
import post_deploy
import utils

# Obsolete.
# from django import newforms as forms
from django import forms
from google.appengine.ext.db import djangoforms


class PostForm(djangoforms.ModelForm):
   title = forms.CharField(
       widget = forms.TextInput(attrs={'id':'name'})
   )
   body = forms.CharField(
       widget = forms.Textarea(
           attrs = { 'id':'message', 'rows': 10, 'cols': 20 }
       )
   )
   body_markup = forms.ChoiceField(
       choices = [(k, v[0]) for k, v in markup.MARKUP_MAP.iteritems()]
   )
   tags = forms.CharField(
       widget = forms.Textarea(attrs = { 'rows': 5, 'cols': 20 })
   )
   draft = forms.BooleanField(required=False)

   class Meta:
      model = models.BlogPost
      fields = [ 'title', 'body', 'tags' ]


def with_post(fun):
   """Decorator for 'get' and 'post' methods of handlers. It retrieves
   a 'BlogPost' object from its id before running 'get' and 'post'."""

   def decorate(self, post_id=None):
      post = None
      if post_id:
         post = models.BlogPost.get_by_id(int(post_id))
         if not post:
            self.error(404)
            return
      fun(self, post)
   return decorate


class BaseHandler(webapp.RequestHandler):
   """The ancestor of handlers to /admin/."""

   def render_to_response(
         self,
         template_name,
         template_vals = None,
         theme = None ):

      if not template_vals:
         template_vals = {}
      template_vals.update({
          'path': self.request.path,
          'handler_class': self.__class__.__name__,
          'is_admin': True,
      })

      # Change 'template_name' to 'admin/template_name' because
      # admin templates are in default/admin.
      template_name = os.path.join('admin', template_name)

      # Send the rendered template as response.
      self.response.out.write(
          utils.render_template(template_name, template_vals, theme)
      )


class AdminHandler(BaseHandler):
  class alternator:
    """A here-class for alternation in Djano templates."""
    def __init__(self, values):
      self.values = values
      self.i = -1
    @property
    def next(self):
      self.i += 1
      return self.values[self.i % len(self.values)]

  def get(self):
    offset = int(self.request.get('start', 0))
    count = int(self.request.get('count', 20))
    posts = models.BlogPost.all().order('-published').fetch(count, offset)
    images = blobstore.BlobInfo.all().order('-creation').fetch(count, offset)
    template_vals = {
        'offset': offset,
        'count': count,
        'last_post': offset + len(posts) - 1,
        'prev_offset': max(0, offset - count),
        'next_offset': offset + count,
        'posts': posts,
        'images': images,
        'upload_url': blobstore.create_upload_url('/admin/upload'),
        'alternator': self.alternator(('odd', 'even')),
    }
    self.render_to_response("index.html", template_vals)


class PostHandler(BaseHandler):
   """Handle the admin queries to admin/post/*."""

   def render_form(self, form):
      # Emit a response with 'form', which is a 'PostForm' object.
      self.render_to_response("edit.html", { 'form': form })

   @with_post
   def get(self, post):
      """GET queries to admin/post/* are to see the form."""

      # NB: 'post' is a 'BlogPost' object.
      self.render_form(PostForm(
           instance = post,
           initial = {
               'draft': post and not post.path,
               'body_markup': post.body_markup if post \
                            else config.default_markup,
           }
      ))

   @with_post
   def post(self, post):
      """POST queries to admin/post/* are to send form data."""

      form = PostForm(
         data = self.request.POST,
         instance = post,
         initial = {'draft': post and post.published is None}
      )

      if not form.is_valid():
         # Form not valid: try again.
         self.render_form(form)
      else:
         # Form is valid, go on and save model to datastore.
         # Create 'post' from 'form' using the 'Meta' class.
         post = form.save(commit=False)
         if form._cleaned_data()['draft']:
            # Post is a draft, publication date is set to max.
            post.published = datetime.datetime.max
            post.put()
         else:
            # Post is not a draft.
            if not post.path:
               # Post had not path: publish.
               post.updated = post.published = datetime.datetime.now()
            else:
               # Post had a path: edit.
               post.updated = datetime.datetime.now()
            # Give post a path, update dependencies and dates.
            post.publish()
         self.render_to_response(
             "published.html",
             {
                 'post': post,
                 'draft': form._cleaned_data()['draft'],
             }
         )


class DeleteHandler(BaseHandler):
  @with_post
  def post(self, post):
    if post.path:# Published post
      post.remove()
    else:# Draft
      post.delete()
    self.render_to_response("deleted.html", None)


class PreviewHandler(BaseHandler):
  @with_post
  def get(self, post):
    # Temporary set a published date iff it's still
    # datetime.max. Django's date filter has a problem with
    # datetime.max and a "real" date looks better.
    if post.published == datetime.datetime.max:
      post.published = datetime.datetime.now()
    self.response.out.write(utils.render_template('post.html', {
        'post': post,
        'is_admin': True}))


class RegenerateHandler(BaseHandler):
  def post(self):
    deferred.defer(post_deploy.PostRegenerator().regenerate)
    deferred.defer(post_deploy.PageRegenerator().regenerate)
    deferred.defer(post_deploy.try_post_deploy, force=True)
    self.render_to_response("regenerating.html")


class PageForm(djangoforms.ModelForm):
  path = forms.RegexField(
    widget=forms.TextInput(attrs={'id':'path'}), 
    regex='(/[a-zA-Z0-9/]+)')
  title = forms.CharField(widget=forms.TextInput(attrs={'id':'title'}))
  template = forms.ChoiceField(choices=config.page_templates.items())
  body = forms.CharField(widget=forms.Textarea(attrs={
      'id':'body',
      'rows': 10,
      'cols': 20}))
  class Meta:
    model = models.Page
    fields = [ 'path', 'title', 'template', 'body' ]

  def clean_path(self):
    data = self._cleaned_data()['path']
    existing_page = models.Page.get_by_key_name(data)
    if not data and existing_page:
      raise forms.ValidationError("The given path already exists.")
    return data


class PageAdminHandler(BaseHandler):
  def get(self):
    offset = int(self.request.get('start', 0))
    count = int(self.request.get('count', 20))
    pages = models.Page.all().order('-updated').fetch(count, offset)
    template_vals = {
        'offset': offset,
        'count': count,
        'prev_offset': max(0, offset - count),
        'next_offset': offset + count,
        'last_page': offset + len(pages) - 1,
        'pages': pages,
    }
    self.render_to_response("indexpage.html", template_vals)


def with_page(fun):
  def decorate(self, page_key=None):
    page = None
    if page_key:
      page = models.Page.get_by_key_name(page_key)
      if not page:
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('404 :(\n' + page_key)
        #self.error(404)
        return
    fun(self, page)
  return decorate


class PageHandler(BaseHandler):
  def render_form(self, form):
    self.render_to_response("editpage.html", {'form': form})

  @with_page
  def get(self, page):
    self.render_form(PageForm(
        instance=page,
        initial={
          'path': page and page.path or '/',
        }))

  @with_page
  def post(self, page):
    form = None
    # if the path has been changed, create a new page
    if page and page.path != self.request.POST['path']:
      form = PageForm(data=self.request.POST, instance=None, initial={})
    else:
      form = PageForm(data=self.request.POST, instance=page, initial={})
    if form.is_valid():
      oldpath = form._cleaned_data()['path']
      if page:
        oldpath = page.path
      page = form.save(commit=False)
      page.updated = datetime.datetime.now()
      page.publish()
      # path edited, remove old stuff
      if page.path != oldpath:
        oldpage = models.Page.get_by_key_name(oldpath)
        oldpage.remove()
      self.render_to_response("publishedpage.html", {'page': page})
    else:
      self.render_form(form)


class PageDeleteHandler(BaseHandler):
  @with_page
  def post(self, page):
    page.remove()
    self.render_to_response("deletedpage.html", None)


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
   """Handle img upload."""

   def post(self):
      """Blob is already uploaded and indexed on the blobstore.
      If the MIME type is image, save it to the datastore, else
      delete."""

      blob_info = self.get_uploads('file')[0]

      # Check that uploaded file is an image. Otherwise delete.
      if re.match('^image/', blob_info.content_type):
         img = models.BlobImage(
                   key_name = blob_info.filename,
                   ref = blob_info.key()
               )
         img.put()
      else:
         blob_info.delete()

      self.redirect("/admin/")
