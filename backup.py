#../google_appengine/remote_api_shell.py thegrandlocus
# From there, do the following.
# from backup import backup
# backup()

import datetime
import os
import pickle

import models

def backup():
   today = datetime.datetime.today()
   Posts = models.BlogPost.all().fetch(1000)
   fname = os.path.join(os.environ['HOME'],
      today.strftime('Dropbox/The_Grand_Locus/posts_%Y%m%d.bkp'))
   pickle.dump(Posts, open(fname, 'w'))
