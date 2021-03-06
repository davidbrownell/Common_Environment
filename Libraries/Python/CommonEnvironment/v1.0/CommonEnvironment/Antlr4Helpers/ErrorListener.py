# ---------------------------------------------------------------------------
# |  
# |  ErrorListener.py
# |  
# |  David Brownell (db@DavidBrownell.com)
# |  
# |  12/15/2015 01:22:57 PM
# |  
# ---------------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2015-18.
# |          
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ---------------------------------------------------------------------------
import os
import sys

import antlr4

# ---------------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ---------------------------------------------------------------------------

class ErrorListener(antlr4.error.ErrorListener.ErrorListener):

    # ---------------------------------------------------------------------------
    # |  Public Types
    class AntlrException(Exception):

        # ----------------------------------------------------------------------
        @classmethod
        def Create( cls, 
                    symbol, 
                    msg=None,
                    source=None,
                  ):
            while not isinstance(symbol, antlr4.Token) and hasattr(symbol, "start"):
                symbol = symbol.start

            return cls( msg or str(symbol), 
                        source or '', 
                        symbol.line, 
                        symbol.column + 1,
                      )

        # ---------------------------------------------------------------------------
        def __init__( self,
                      msg,
                      source,
                      line,
                      column,
                    ):
            super(ErrorListener.AntlrException, self).__init__("{msg} ({source} [{line} <{column}>])".format(**locals()))
    
    # ---------------------------------------------------------------------------
    # |  Public Methods
    def __init__(self, source, *args, **kwargs):
        super(ErrorListener, self).__init__(*args, **kwargs)
        self._source                        = source

    # ---------------------------------------------------------------------------
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise ErrorListener.AntlrException( msg,
                                            self._source,
                                            line,
                                            column + 1,
                                          )
