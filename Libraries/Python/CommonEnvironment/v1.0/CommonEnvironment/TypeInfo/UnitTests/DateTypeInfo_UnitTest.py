# ---------------------------------------------------------------------------
# |  
# |  DateTypeInfo_UnitTest.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  12/29/2015 04:18:49 PM
# |  
# ---------------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2015.
# |          
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ---------------------------------------------------------------------------
"""Unit test for DateTypeInfo.py
"""

import os
import sys
import unittest

from CommonEnvironment import Package

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

__package__ = Package.CreateName(__package__, __name__, __file__)
from ..DateTypeInfo import *
__package__ = None

# ---------------------------------------------------------------------------
class FundamentalDate(unittest.TestCase):

    # ---------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        cls._type_info = DateTypeInfo()

    # ---------------------------------------------------------------------------
    def test_Validate(self):
        self._type_info.Validate(self._type_info.Create())
        self.assertRaises(Exception, lambda: self._type_info.Validate("wrong type"))
        self.assertRaises(Exception, lambda: self._type_info.Validate(10))

    # ---------------------------------------------------------------------------
    def test_StringConversion(self):
        now = self._type_info.Create()
        self.assertEqual(now, self._type_info.ItemFromString(self._type_info.ItemToString(now)))

    # ---------------------------------------------------------------------------
    def test_PythonDefinitionString(self):
        self.assertEqual(self._type_info.PythonDefinitionString, r'DateTypeInfo(arity=Arity(min=1, max_or_none=1))')
        
    # ---------------------------------------------------------------------------
    def test_ConstraintsDesc(self):
        self.assertEqual(self._type_info.ConstraintsDesc, "")
        
    # ---------------------------------------------------------------------------
    def test_PythonItemRegularExpressionStrings(self):
        self.assertEqual(self._type_info.PythonItemRegularExpressionStrings, "[0-9]{4}-(0?[1-9]|1[0-2])-([0-2][0-9]|3[0-1])")
        
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(unittest.main(verbosity=2))
    except KeyboardInterrupt: pass