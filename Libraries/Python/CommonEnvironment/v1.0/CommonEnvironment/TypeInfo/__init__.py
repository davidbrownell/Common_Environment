# ----------------------------------------------------------------------
# |  
# |  __init__.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2016-09-04 17:12:58
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2016-18.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
import inflect
import os
import sys

import six

from CommonEnvironment.Interface import *

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

Plural = inflect.engine()

# ----------------------------------------------------------------------
# |  
# |  Public Types
# |  
# ----------------------------------------------------------------------
class ValidationException(Exception):
    pass

# ----------------------------------------------------------------------
class Arity(object):

    # ----------------------------------------------------------------------
    @classmethod
    def FromString(cls, value):
        if value == '?':
            return cls(0, 1)

        if value == '1':
            return cls(1, 1)

        if value == '*':
            return cls(0, None)

        if value == '+':
            return cls(1, None)

        if value.startswith('(') and value.endswith(')'):
            values = [ int(v.strip()) for v in value[1:-1].split(',') ]

            if len(values) == 1:
                return cls(values[0], values[0])
            elif len(values) == 2:
                return cls(values[0], values[1])

        raise Exception("'{}' is not a valid arity".format(value))

    # ----------------------------------------------------------------------
    def __init__(self, min, max_or_none):
        if max_or_none != None and min > max_or_none:
            raise Exception("Invalid argument - 'max_or_none'")

        self.Min                            = min
        self.Max                            = max_or_none

    # ----------------------------------------------------------------------
    def __str__(self):
        return "Arity({}, {})".format(self.Min, self.Max)

    # ----------------------------------------------------------------------
    @property
    def IsSingle(self):
        return self.Min == 1 and self.Max == 1

    @property
    def IsOptional(self):
        return self.Min == 0 and self.Max == 1

    @property
    def IsCollection(self):
        return self.Max == None or self.Max > 1

    @property
    def IsOptionalCollection(self):
        return self.IsCollection and self.Min == 0

    @property
    def IsFixedCollection(self):
        return self.IsCollection and self.Min == self.Max

    @property
    def IsZeroOrMore(self):
        return self.Min == 0 and self.Max == None

    @property
    def IsOneOrMore(self):
        return self.Min == 1 and self.Max == None

    @property
    def IsRange(self):
        return self.Max != None and self.Min != self.Max

    @property
    def PythonDefinitionString(self):
        return "Arity(min={}, max_or_none={})".format(self.Min, self.Max)

    # ----------------------------------------------------------------------
    def ToString( self,
                  brackets=None,            # ( lbraket, rbracket )
                ):
        brackets = brackets or ( '(', ')' )

        if self.IsOptional:
            return '?'
        elif self.IsZeroOrMore:
            return '*'
        elif self.IsOneOrMore:
            return '+'
        elif self.IsSingle:
            return ''
        elif self.Min == self.Max:
            return "{}{}{}".format( brackets[0], 
                                    self.Min, 
                                    brackets[1],
                                  )
        else:
            return "{}{},{}{}".format( brackets[0],
                                       self.Min, 
                                       self.Max,
                                       brackets[1],
                                     )

    # ----------------------------------------------------------------------
    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return -1

        if self.Min == None:
            if other.Min != None:
                return -1
        else:
            if other.Min == None:
                return 1

            if self.Min < other.Min:
                return -1
            elif other.Min < self.Min:
                return 1

        if self.Max == None:
            if other.Max != None:
                return 1
        else:
            if other.Max == None:
                return -1

            if self.Max < other.Max:
                return -1
            elif self.Max > other.Max:
                return 1

        assert self.Min == other.Min, (self.Min, other.Min)
        assert self.Max == other.Max, (self.Max, other.Max)

        return 0

    # ----------------------------------------------------------------------
    def __lt__(self, other):
        return self.__cmp__(other) < 0

    # ----------------------------------------------------------------------
    def __eq__(self, other):
        return self.__cmp__(other) == 0

# ----------------------------------------------------------------------
class TypeInfo(Interface):
    
    # ----------------------------------------------------------------------
    # |  
    # |  Public Properties
    # |  
    # ----------------------------------------------------------------------
    @abstractproperty
    def Desc(self):
        raise Exception("Abstract property")

    # In theory, this should be an abstract property. However, some implementations
    # have a callable ExpectedType, which will cause Interface validation to fail.
    # If someone forgets to implement this property/method, they will see an exception
    # raised on the first invocation.
    #
    # @abstractproperty
    def ExpectedType(self):
        raise Exception("Abstract property")

    @abstractproperty
    def ConstraintsDesc(self):
        raise Exception("Abstract property")

    @abstractproperty
    def PythonDefinitionString(self):
        raise Exception("Abstract property")

    # ----------------------------------------------------------------------
    # |  
    # |  Public Methods
    # |  
    # ----------------------------------------------------------------------
    def __init__( self,
                  arity=None,                           # default is Arity(1, 1)
                  validation_func=None,                 # def Func(value) -> string on error
                  collection_validation_func=None,      # def Func(values) -> string on error
                ):
        if isinstance(arity, six.string_types):
            arity = Arity.FromString(arity)
        else:
            arity = arity or Arity(1, 1)

        if collection_validation_func and not arity.IsCollection:
            raise Exception("'collection_validation_func' should only be used for types that are collections")
        
        self.Arity                          = arity or Arity(1, 1)
        self.ValidationFunc                 = validation_func
        self.CollectionValidationFunc       = collection_validation_func
        
    # ----------------------------------------------------------------------
    def IsExpectedType(self, item):
        if self._ExpectedTypeIsCallable:
            return self.ExpectedType(item)
        
        return isinstance(item, self.ExpectedType)

    # ----------------------------------------------------------------------
    def IsValid(self, item_or_items):
        return self.ValidateNoThrow(item_or_items) == None

    # ----------------------------------------------------------------------
    def IsValidItem(self, item):
        return self.ValidateItemNoThrow(item) == None

    # ----------------------------------------------------------------------
    def Validate(self, value, **custom_args):
        result = self.ValidateNoThrow(value, **custom_args)
        if result != None:
            raise ValidationException(result)

    # ----------------------------------------------------------------------
    def ValidateArity(self, value):
        result = self.ValidateArityNoThrow(value)
        if result != None:
            raise ValidationException(result)

    # ----------------------------------------------------------------------
    def ValidateArityCount(self, count):
        result = self.ValidateArityCountNoThrow(count)
        if result != None:
            raise ValidationException(result)

    # ----------------------------------------------------------------------
    def ValidateItem(self, value, **custom_args):
        result = self.ValidateItemNoThrow(value, **custom_args)
        if result != None:
            raise ValidationException(result)

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def ValidateNoThrow(self, value, **custom_args):
        result = self.ValidateArityNoThrow(value)
        if result != None:
            return result

        if not self.Arity.IsCollection:
            value = [ value, ]
        elif value == None:
            value = []

        if self.CollectionValidationFunc:
            result = self.CollectionValidationFunc(value)
            if result != None:
                return result

        for item in value:
            result = self.ValidateItemNoThrow(item, **custom_args)
            if result != None:
                return result

    # ----------------------------------------------------------------------
    def ValidateArityNoThrow(self, value):
        if not self.Arity.IsCollection and isinstance(value, list):
            return "Only 1 item was expected"

        return self.ValidateArityCountNoThrow(len(value) if isinstance(value, list) else 1 if value != None else 0)

    # ----------------------------------------------------------------------
    def ValidateArityCountNoThrow(self, count):
        if not self.Arity.IsCollection:
            if(count == 0 and not self.Arity.IsOptional) or count > 1:
                return "1 item was expected"

            return 

        if self.Arity.Min != None and count < self.Arity.Min:
            return "At least {} {} expected".format( Plural.no("item", self.Arity.Min),
                                                     Plural.plural_verb("was", self.Arity.Min),
                                                   )

        if self.Arity.Max != None and count > self.Arity.Max:
            return "At most {} {} expected".format( Plural.no("item", self.Arity.Max),
                                                    Plural.plural_verb("was", self.Arity.Max),
                                                  )

    # ----------------------------------------------------------------------
    def ValidateItemNoThrow(self, item, **custom_args):
        if self.Arity.IsOptional and item == None:
            return

        if not self.IsExpectedType(item):
            return "'{}' is not {}".format( item,
                                            Plural.a(self._GetExpectedTypeString()),
                                          )

        result = self._ValidateItemNoThrowImpl(item, **custom_args)
        if result != None:
            return result

        if self.ValidationFunc:
            result = self.ValidationFunc(item)
            if result != None:
                return result

    # ----------------------------------------------------------------------
    # |  
    # |  Protected Properties
    # |  
    # ----------------------------------------------------------------------
    _ExpectedTypeIsCallable                 = False

    @property
    def _PythonDefinitionStringContents(self):
        # Arbitrary custom validation functions can't be saved as part of a
        # generic python definitions
        assert not self.ValidationFunc
        assert not self.CollectionValidationFunc

        return "arity={}".format(self.Arity.PythonDefinitionString)

    # ----------------------------------------------------------------------
    # |  
    # |  Protected Methods
    # |  
    # ----------------------------------------------------------------------
    def _GetExpectedTypeString(self):
        # ----------------------------------------------------------------------
        def GetTypeName(t):
            return getattr(t, "__name__", str(t))

        # ----------------------------------------------------------------------
        
        if self._ExpectedTypeIsCallable:
            return self.__class__.__name__

        if isinstance(self.ExpectedType, tuple):
            return ', '.join([ GetTypeName(t) for t in self.ExpectedType ])

        return GetTypeName(self.ExpectedType)
        
    # ----------------------------------------------------------------------
    # |  
    # |  Private Methods
    # |  
    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _ValidateItemNoThrowImpl(item, **custom_args):
        """Return string on error"""
        raise Exception("Abstract method")
    