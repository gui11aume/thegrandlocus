#! -*- coding: utf-8 -*-
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' 

from google.appengine.dist import use_library
use_library('django', '1.3')
