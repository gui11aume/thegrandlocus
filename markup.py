# -*- coding:utf-8 -*-

"""
Support for different markup languages for the body of a post.

The following markup languages are supported:
 - HTML
 - Markdown

For ReStructuredText and Markdown syntax highlighting of source code is
available.
"""

# TODO: Add summary rendering.
# TODO: Docstrings.

import re

import config

# Import markup module from lib/
import markdown
import markdown_processor

from HTMLEditor import HTMLWordTruncator


CUT_SEPARATOR_REGEX = r'<!--.*cut.*-->'


def render_markdown(content):
  md = markdown.Markdown()
  md.textPreprocessors.insert(0, markdown_processor.CodeBlockPreprocessor())
  return md.convert(content)


# Mapping: string ID -> (human readable name, renderer)
MARKUP_MAP = {
    'html':     ('HTML', lambda c: c),
    'markdown': ('Markdown', render_markdown),
}


def get_renderer(post):
  """Returns a render function for this posts body markup."""
  return MARKUP_MAP.get(post.body_markup)[1]


def clean_content(content):
  """Clean up the raw body.
  Actually this removes the cut separator.
  """
  return re.sub(CUT_SEPARATOR_REGEX, '', content)


def render_body(post):
  """Return the post's body rendered to HTML."""
  renderer = get_renderer(post)
  return renderer(clean_content(post.body))


def render_summary(post):
  """Return the post's summary rendered to HTML."""
  renderer = get_renderer(post)
  match = re.search(CUT_SEPARATOR_REGEX, post.body)
  if match:
    return renderer(post.body[:match.start(0)])
  else:
    truncator = HTMLWordTruncator(config.summary_length)
    return truncator.process(renderer(clean_content(post.body)))
