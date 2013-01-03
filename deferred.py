#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Request handler module for the deferred library.

See deferred.py for full documentation.
"""



#import setup_django_version

from google.appengine.ext import deferred
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path

def main():
  fix_path.fix_sys_path()
  run_wsgi_app(deferred.application)


if __name__ == "__main__":
  main()

