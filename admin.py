#import setup_django_version

import webapp2

import config
import post_deploy
import handlers

#post_deploy.run_deploy_task()

app = webapp2.WSGIApplication([
  (config.url_prefix + '/admin/', handlers.AdminHandler),
  (config.url_prefix + '/admin/posts', handlers.AdminHandler),
  (config.url_prefix + '/admin/upload', handlers.UploadHandler),
  (config.url_prefix + '/admin/pages', handlers.PageAdminHandler),
  (config.url_prefix + '/admin/newpost', handlers.PostHandler),
  (config.url_prefix + '/admin/post/(\d+)', handlers.PostHandler),
  (config.url_prefix + '/admin/regenerate', handlers.RegenerateHandler),
  (config.url_prefix + '/admin/stagefeed', handlers.FeedStageHandler),
  (config.url_prefix + '/admin/commitfeed', handlers.FeedCommitHandler),
  (config.url_prefix + '/admin/post/delete/(\d+)', handlers.DeleteHandler),
  (config.url_prefix + '/admin/post/feed/(\d+)', handlers.FeedHandler),
  (config.url_prefix + '/admin/post/preview/(\d+)', handlers.PreviewHandler),
  (config.url_prefix + '/admin/delete/(.*)', handlers.DeleteImgHandler),
#  (config.url_prefix + '/admin/newpage', handlers.PageHandler),
#  (config.url_prefix + '/admin/page/delete/(/.*)', handlers.PageDeleteHandler),
#  (config.url_prefix + '/admin/page/(/.*)', handlers.PageHandler),
])
