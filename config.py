# Name of the blog
blog_name = 'The Grand Locus'

# Your name (used for copyright info)
author_name = 'Guillaume Filion'

# (Optional) slogan
slogan = 'Life for statistical sciences'

# The hostname this site will primarially serve off (used for Atom feeds)
host = 'blog.thegrandlocus.com'

# Defines the URL organization to use for blog postings. Valid substitutions:
#   slug - the identifier for the post, derived from the title
#   year - the year the post was published in
#   month - the month the post was published in
#   day - the day the post was published in
post_path_format = '/%(year)d/%(month)02d/%(slug)s'

# Number of entries per page in indexes.
posts_per_page = 10

# The mime type to serve HTML files as.
html_mime_type = "text/html; charset=utf-8"

# Length (in words) of summaries, by default
summary_length = 198

# Default markup language for entry bodies (defaults to html).
# TODO <================= delete this!
default_markup = 'markdown'

# Syntax highlighting style for RestructuredText and Markdown,
# one of 'manni', 'perldoc', 'borland', 'colorful', 'default', 'murphy',
# 'vs', 'trac', 'tango', 'fruity', 'autumn', 'bw', 'emacs', 'pastie',
# 'friendly', 'native'.
highlighting_style = 'friendly'

# Absolute url of the blog application use '/blog' for host/blog/
# and '' for host/. Also remember to change app.yaml accordingly
# TODO <================ delete this!
url_prefix = ''

# Defines where the user is defined in the rel="me" of your pages.
# This allows you to expand on your social graph.
rel_me = "Guillaume Filion"

# To format the date of your post.
# http://docs.djangoproject.com/en/1.1/ref/templates/builtins/#now
date_format = "%d %B %Y"
