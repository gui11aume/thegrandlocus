# -*- coding:utf-8 -*-

# Extends 'sys.path' to include the 'lib' directory.
# Because modules are imported a single time, this makes sure that
# the path is extended only once.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
