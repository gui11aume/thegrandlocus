import markdown
import re

import config

from HTMLEditor import HTMLWordTruncator
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments import highlight

CUT_SEPARATOR_REGEX = r"<!-- CUT_SEPARATOR -->"


# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False
LINEENDING = '<br />'


class CodeBlockPreprocessor(markdown.preprocessors.Preprocessor):
  def run(self, lines):
    pattern = re.compile(
        r"\s*\[sourcecode:(.+?)\](.+?)\[/sourcecode\]\s*", re.S
    )
    formatter = HtmlFormatter(noclasses=INLINESTYLES, lineseparator=LINEENDING)
    def repl(m):
      try:
          lexer = get_lexer_by_name(m.group(1))
      except ValueError:
          lexer = TextLexer()
      code = highlight(m.group(2), lexer, formatter)
      i = code.rfind("%s</pre></div>" % LINEENDING)
      code = code[:i] + code[i+len(LINEENDING):]
      return "\n\n%s\n\n" % code.strip()
    return [pattern.sub(repl, line) for line in lines]


class MathJaxCodeBlockPreprocessor(CodeBlockPreprocessor):
   # My mathjax delimiters are "$(" and ")$". Escape the
   # "\" and "_" that are inside.
   def __init__(self, delimiters, *args, **kwargs):
      self.delimiters = delimiters
      super.__init__(args, kwargs)

   def run(self, lines):
      def repl(m):
         m.group().replace('\\', '\\\\').replace('_', '\\_')
      pattern = re.compile(
          r'%s.+?%s' % tuple([re.escape(a) for a in self.delimiters]),
          re.S
      )
      CodeBlockPreprocessor.run(self, pattern.sub(repl, lines))


md = markdown.Markdown()
md.preprocessors.register(CodeBlockPreprocessor(md), "CodeBlockPreprocessor", 0)


def render_body(post):
  """Return the post's body rendered to HTML."""
  return md.convert(re.sub(CUT_SEPARATOR_REGEX, "", post.body))


def render_summary(post):
  """Return the post's summary rendered to HTML."""
  match = re.search(CUT_SEPARATOR_REGEX, post.body)
  if match:
    return md.convert(post.body[:match.start(0)])
  else:
    truncator = HTMLWordTruncator(config.summary_length)
    return truncator.process(md.convert(post.body))
