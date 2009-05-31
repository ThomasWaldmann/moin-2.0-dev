#! /usr/bin/env python

# as we require Python 2.5 now, we'll have a try with the code from stdlib:
from difflib import *

# The code that used to live here, had this comment:
# Python 2.4.3 (maybe other versions, too) has a broken difflib, sometimes
# raising a "maximum recursion depth exceeded in cmp" exception.
# This is taken from python.org SVN repo revision 54230 with patches
# 36160 and 34415 reversed for python2.3 compatibility.
# Also, startswith(tuple) [2.5] was changed to multiple startswith(elem).

