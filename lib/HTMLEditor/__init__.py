# -*- coding:utf-8 -*-

import re
import sys

from StringIO import StringIO
from HTMLParser import HTMLParser
from HTMLParser import HTMLParseError


class StopStreaming(Exception):
   """Exception class used to interrupt streaming in objects of class
   'HTMLStreamer'."""
   pass


class HTMLStreamer(HTMLParser):
   """A basic HTML stream parser.
   Redirects unmodified HTML to output stream. This can be used
   to stream HTML to a file, or to return a 'str' object upon calling
   'process'."""

   # Constructor.
   def __init__(self, out=StringIO()):
      self.data = ''
      self.out = out
      HTMLParser.__init__(self)

   # Basic HTML handling functions.
   def handle_charref(self, name):
      self.data += '&#%s;' % name
   def handle_comment(self, data):
      self.flushdata()
      self.out.write('<!--%s-->' % data)
   def handle_data(self, data):
      self.data += data
   def handle_decl(self, decl):
      self.out.write('<!%s>' % decl)
   def handle_endtag(self, tag):
      self.flushdata()
      self.out.write('</%s>' % tag)
   def handle_entityref(self, name):
      self.data += '&%s;' % name
   def handle_pi(self, data):
      self.flushdata()
      self.out.write('<?%s>' % data)
   def handle_startendtag(self, tag, attrs):
      self.flushdata()
      self.out.write('<%s%s />' % (tag, self.fmt(attrs)))
   def handle_starttag(self, tag, attrs):
      self.flushdata()
      self.out.write('<%s%s>' % (tag, self.fmt(attrs)))
   def flushdata(self):
      self.out.write(self.data)
      self.data = ''
   def fmt(self, attrs):
      return ''.join([' %s="%s"' % pair for pair in attrs])

   def process(self, html):
      """Parses 'html' with handlers and return a 'str' object."""
      (out, self.out) = (self.out, StringIO())
      try:
         self.feed(html)
      except StopStreaming:
         pass
      finally:
         (out, self.out) = (self.out, out)
      return out.getvalue()


class StackedHTMLStreamer(HTMLStreamer):
   """Extends 'HTMLStreamer' by keeping track of open tags in a
   stack."""

   # Constructor.
   def __init__(self, *args, **kwargs):
      self.stack = []
      HTMLStreamer.__init__(self, *args, **kwargs)

   # Overwritten methods.
   def handle_starttag(self, tag, attrs):
      self.stack.append(tag)
      HTMLStreamer.handle_starttag(self, tag, attrs)
   def handle_endtag(self, tag):
      if tag != self.stack.pop():
         raise HTMLParseError('unexpected endtag %s' % tag)
      HTMLStreamer.handle_endtag(self, tag)

   # New method.
   def close_open_tags(self):
      """Close all open tags in 'stack' in output stream.
      NOTE: further streaming woud break the HTML syntax."""
      for tag in reversed(self.stack):
         HTMLStreamer.handle_endtag(self, tag)


class HTMLWordTruncator(StackedHTMLStreamer):
   """Extends 'StackedHTMLStreamer' by raising a 'StopStreaming'
   exception when more words than specified have been streamed
   from HTML data.
   Words here are defined as symbols separated by punctuation or
   white spaces (symbols delimited by the regular expression'\B')."""

   # Constructor.
   def __init__(self, maxnwords=None, *args, **kwargs):
      self.maxnwords = float('inf') if maxnwords is None else maxnwords
      StackedHTMLStreamer.__init__(self, *args, **kwargs)

   # Overwritten method.
   def flushdata(self):
      """Counts words in streamed data and when too many words have
      been streamed closes all open tags and raises 'StopStreaming'."""
      nwords = len(re.findall(r'\B', self.data))/2
      if self.maxnwords < nwords:
         for num,match in enumerate(re.finditer(r'\B', self.data)):
            if num/2 >= self.maxnwords: break
         self.data = self.data[:match.pos]
         StackedHTMLStreamer.flushdata(self)
         self.close_open_tags()
         raise StopStreaming
      else:
         self.maxnwords -= nwords
         StackedHTMLStreamer.flushdata(self)


class URLAbsolutifier(HTMLStreamer):
   """Extends 'HTMLStreamer' by replacing "href" and "src" attributes
   by a specified absolute domain name."""

   def __init__(self, domain, *args, **kwargs):
      if not domain.startswith('http'): domain = 'http://' + domain
      self.domain = re.sub('/?$', '/', domain)
      HTMLStreamer.__init__(self, *args, **kwargs)

   def fmt(self, attrs):
      attrs = dict(attrs)
      _rel = r'^(/|\.|#)'
      _abs = r'%s\1' % self.domain
      for key in ('src', 'href'):
         if key in attrs: attrs[key] = re.sub(_rel, _abs, attrs[key])
      return HTMLStreamer.fmt(self, attrs.items())
