# ----------------------------------------------------------------------
# |  
# |  Jinja2CodeGenerator.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2016-02-15 19:17:35
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2016-18.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
import hashlib
import itertools
import os
import sys
import textwrap

from collections import OrderedDict

import six

from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Interface
from CommonEnvironment.QuickObject import QuickObject
from CommonEnvironment.StreamDecorator import StreamDecorator

from CommonEnvironment.Compiler import CodeGenerator as CodeGeneratorMod
from CommonEnvironment.Compiler.InputProcessingMixin.AtomicInputProcessingMixin import AtomicInputProcessingMixin
from CommonEnvironment.Compiler.InvocationQueryMixin.ConditionalInvocationQueryMixin import ConditionalInvocationQueryMixin
from CommonEnvironment.Compiler.InvocationMixin.CustomInvocationMixin import CustomInvocationMixin
from CommonEnvironment.Compiler.OutputMixin.MultipleOutputMixin import MultipleOutputMixin

from jinja2 import DebugUndefined, \
                   Environment, \
                   exceptions, \
                   FileSystemLoader, \
                   make_logging_undefined, \
                   StrictUndefined, \
                   Undefined

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ---------------------------------------------------------------------------
# |
# |  Public Types
# |
# ---------------------------------------------------------------------------
@Interface.staticderived
class CodeGenerator( AtomicInputProcessingMixin,
                     ConditionalInvocationQueryMixin,
                     CustomInvocationMixin,
                     MultipleOutputMixin,
                     CodeGeneratorMod.CodeGenerator,
                   ):
    # ---------------------------------------------------------------------------
    # |
    # |  Public Properties
    # |
    # ---------------------------------------------------------------------------
    Name                                    = "Jinja2CodeGenerator"
    Description                             = "Processes a Jinja2 template and produces output"
    Type                                    = CodeGeneratorMod.CodeGenerator.TypeValue.File

    # ---------------------------------------------------------------------------
    # |
    # |  Public Methods
    # |
    # ---------------------------------------------------------------------------
    @staticmethod
    def IsSupported(item):
        if not os.path.isfile(item):
            return False

        return "Jinja2" in item.split('.')

    # ---------------------------------------------------------------------------
    # |
    # |  Private Methods
    # |
    # ---------------------------------------------------------------------------
    
    # ---------------------------------------------------------------------------
    @classmethod
    def _GetOptionalMetadata(cls):
        return [ ( "jinja2_context", {} ),
                 ( "jinja2_context_code", [] ),
                 ( "preserve_dir_structure", False ),
                 ( "ignore_errors", False ),
                 ( "debug", False ),
               ] + \
               super(CodeGenerator, cls)._GetOptionalMetadata()

    # ---------------------------------------------------------------------------
    @classmethod
    def _PostprocessContextItem(cls, context):
        jinja2_context = {}

        # Load the custom context defined in code
        for context_code in context.jinja2_context_code:
            dirname, filename = os.path.split(context_code.filename)

            sys.path.insert(0, dirname)
            with CallOnExit(lambda: sys.path.pop(0)):
                mod = __import__(os.path.splitext(filename)[0])

            var = getattr(mod, context_code.var_name)
            del mod

            if isinstance(var, dict):
                for k, v in six.iteritems(var):
                    jinja2_context[k] = v
            else:
                jinja2_context[context_code.var_name] = var

        del context.jinja2_context_code

        # Load the custom context
        for k, v in six.iteritems(context.jinja2_context):
            if len(v) == 1:
                jinja2_context[k] = v[0]
            else:
                jinja2_context[k] = v

        context.jinja2_context = jinja2_context

        # Calculate the hashes. We won't use this is the code below, but it
        # will be used during comparison to determine if an input file has
        # changed.

        # ----------------------------------------------------------------------
        def CalculateHash(input_filename):
            with open(input_filename, 'rb') as f:
                return hashlib.sha256(f.read()).digest()

        # ----------------------------------------------------------------------

        context.hashes = [ CalculateHash(input_filename) for input_filename in context.input_filenames ]

        # Get the output filenames
        if not context.preserve_dir_structure:
            # ----------------------------------------------------------------------
            def GetBaseDir(input_filename):
                return ''

            # ----------------------------------------------------------------------
        else:
            if len(context.input_filenames) == 1:
                common_prefix = os.path.dirname(context.input_filenames[0])
            else:
                common_prefix = FileSystem.GetCommonPath(*context.input_filenames)

            # ----------------------------------------------------------------------
            def GetBaseDir(input_filename):
                dirname = os.path.dirname(input_filename)

                assert dirname.startswith(common_prefix), (dirname, common_prefix)
                dirname = dirname[len(common_prefix):]

                if dirname.startswith(os.path.sep):
                    dirname = dirname[len(os.path.sep):]

                return dirname

            # ----------------------------------------------------------------------
            
        output_filenames = []

        for input_filename in context.input_filenames:
            output_filenames.append(os.path.join( context.output_dir,
                                                  GetBaseDir(input_filename),
                                                  '.'.join([ part for part in os.path.basename(input_filename).split('.') if part != "Jinja2" ]),
                                                ))


        context.output_filenames = output_filenames

        return super(CodeGenerator, cls)._PostprocessContextItem(context)

    # ----------------------------------------------------------------------
    @staticmethod
    def _CustomContextComparison(context, prev_context):
        return

    # ---------------------------------------------------------------------------
    @classmethod
    def _InvokeImpl( cls,
                     invoke_reason,
                     context,
                     status_stream,
                     verbose_stream,
                     verbose,
                   ):
        # ----------------------------------------------------------------------
        class RelativeFileSystemLoader(FileSystemLoader):
            
            # ----------------------------------------------------------------------
            def __init__( self, 
                          input_filename, 
                          searchpath=None,
                          *args, 
                          **kwargs
                        ):
                super(RelativeFileSystemLoader, self).__init__( searchpath=[ os.path.dirname(input_filename), ] + (searchpath or []),
                                                                *args, 
                                                                **kwargs
                                                              )

            # ----------------------------------------------------------------------
            def get_source(self, environment, template):
                method = super(RelativeFileSystemLoader, self).get_source

                try:
                    return method(environment, template)

                except exceptions.TemplateNotFound:
                    for searchpath in reversed(self.searchpath):
                        potential_template = os.path.normpath(os.path.join(searchpath, template).replace('/', os.path.sep))
                        if os.path.isfile(potential_template):
                            dirname, template = os.path.split(potential_template)

                            self.searchpath.append(dirname)
                            return method(environment, template)

                    raise

        # ----------------------------------------------------------------------

        with status_stream.DoneManager( display=False,
                                      ) as dm:
            for index, (input_filename, output_filename) in enumerate(six.moves.zip( context.input_filenames,
                                                                                     context.output_filenames,
                                                                                   )):
                status_stream.write("Processing '{}' ({} of {})...".format( input_filename,
                                                                            index + 1,
                                                                            len(context.output_filenames),
                                                                          ))
                with dm.stream.DoneManager( suppress_exceptions=True,
                                          ) as this_dm:
                    try:
                        # ----------------------------------------------------------------------
                        def ReadFileFilter(value):
                            potential_filename = os.path.join(os.path.dirname(input_filename), value)
                            if not os.path.isfile(potential_filename):
                                return "<< '{}' was not found >>".format(potential_filename)
            
                            return open(potential_filename).read()
            
                        # ----------------------------------------------------------------------

                        loader = RelativeFileSystemLoader(input_filename)

                        if context.debug:
                            from jinja2 import meta

                            env = Environment(loader=loader)

                            content = env.parse(open(input_filename).read())
                            
                            this_dm.stream.write("Variables:\n{}\n".format('\n'.join([ "    - {}".format(var) for var in meta.find_undeclared_variables(content) ])))
                            
                            continue

                        elif context.ignore_errors:
                            undef = Undefined
                        else:
                            undef = StrictUndefined

                        env = Environment( trim_blocks=True,
                                           lstrip_blocks=True,
                                           loader=loader,
                                           undefined=undef,
                                         )
            
                        env.tests["valid_file"] = lambda value: os.path.isfile(os.path.join(os.path.dirname(input_filename), value))
                        env.filters["doubleslash"] = lambda value: value.replace('\\', '\\\\')
                        
                        # Technically speaking, this isn't required as Jinja's import/include/extend functionality
                        # superseeds this functionality. However, it remains in the name of backwards compatibility.
                        env.filters["read_file"] = ReadFileFilter
                        
                        template = env.from_string(open(input_filename).read())
                        
                        try:
                            content = template.render(**context.jinja2_context)
                        except exceptions.UndefinedError as ex:
                            this_dm.stream.write("ERROR: {}\n".format(str(ex)))
                            this_dm.result = -1

                            continue

                        with open(output_filename, 'w') as f:
                            f.write(content)
            
                    except:
                        this_dm.result = -1
                        raise
            
            return dm.result

# ---------------------------------------------------------------------------
# |
# |  Public Methods
# |
# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( input=CommandLine.FilenameTypeInfo(match_any=True, arity='+'),
                                  output_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                                  context=CommandLine.DictTypeInfo(require_exact_match=False, arity='?'),
                                  context_code=CommandLine.StringTypeInfo(validation_expression="^.+:.+$", arity='*'),
                                  output_stream=None,
                                )
def Generate( input,                          # <Redefining build-in type> pylint: disable = W0622
              output_dir,
              context=None,
              context_code=None,
              preserve_dir_structure=False,
              ignore_errors=False,
              debug=False,
              force=False,
              output_stream=sys.stdout,
              verbose=False,
            ):
    context_code = [ item.rsplit(':', 1) for item in context_code ]
    context_code = [ QuickObject( filename=item[0],
                                  var_name=item[1],
                                )
                     for item in context_code
                   ]

    return CodeGeneratorMod.CommandLineGenerate( CodeGenerator,
                                                 input,
                                                 output_stream,
                                                 verbose,

                                                 output_dir=output_dir,
                                                 force=force,

                                                 jinja2_context=context,
                                                 jinja2_context_code=context_code,
                                                 preserve_dir_structure=preserve_dir_structure,
                                                 ignore_errors=ignore_errors,
                                                 debug=debug,
                                               )

# ---------------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.FunctionConstraints( output_dir=CommandLine.DirectoryTypeInfo(),
                                  output_stream=None,
                                )
def Clean( output_dir,
           output_stream=sys.stdout,
         ):
    return CodeGeneratorMod.CommandLineClean(output_dir, output_stream)

# ----------------------------------------------------------------------
def CommandLineSuffix():
    return StreamDecorator.LeftJustify( textwrap.dedent(
                                            """\
                                            Where <context_code> is in the form:
                                                <filename>:<var_name>

                                                Example:
                                                    /Location/Of/Python/File:var_in_file
                                                    C:\My\Dir\Location:ContextData

                                            """),
                                        4,
                                        skip_first_line=False,
                                      )

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass
