#!/bin/env python2.7
"""Command-line tool (and library) to identify imports in Python source files.
   By Jeff Rush <jrush@taupro.com>

   This program reports how imports within a collection of Python source files
   relate to each other, module-to-module as well as
   distribution-to-distribution.  The output can be a textual report as well
   as a graphical representation of the relationships.

   Copyright 2013 Tau Productions Inc.
"""

import sys
import os
import re
import types
import commands
import ast
import logging
import inspect

from collections import defaultdict
from optparse import OptionParser

from filesys_utils import (
    walktrees,
    pkgname_from_src_filename,
    distro_dir_and_name_from_src_filename,
    dottedname_uplevel,
)

logger = logging.getLogger('imports')


class ImportsOptionParser(OptionParser):
    """Command-line arguments accepted by this 'imports' program.
    """

    usage = "usage: %prog [options]"

    def __init__(self, **kw):
        OptionParser.__init__(self, **kw)

        self.add_option("-n", "--dry-run",
                        action="store_true", dest="dry_run", default=False,
                        help=("skip any changes to files, just report results"))

        self.add_option("-v", "--verbose",
                        action="store_true", dest="verbose", default=False,
                        help=("show details of problems, not just summary counts"))

        self.add_option("-u", "--unused-imports",
                        action="store_true", dest="unused_imports", default=False,
                        help=(
                            "report imports statically found in source that are never used in the code"
                        )
            )

        self.add_option("--static-imports",
                        action="store_true", dest="static_imports", default=False,
                        help=(
                            "report all imports, whether used or not"
                        )
            )

        self.add_option("--run",
                        action="store", dest="run", default=None,
                        help=("hook import machinery and run this program to see what gets imported."))

        self.add_option("--ignore-stdlib",
                        action="store_true", dest="ignore_stdlib", default=False,
                        help=("ignore imports from the Python standard library."))

        self.add_option("--ignore-internal-imports",
                        action="store_true", dest="ignore_internal_imports", default=False,
                        help=("ignore imports within a package."))


class DistributionNames(object):
    """Given a src pathname, figure out its distribution name, stash and return it.

       Given the full pathname to a source file, figure out what distribution (egg)
       it belongs to, by examining various nearby files, and return that name.

       The name is remembered to construct the set of all unique distribution
       names found, for reporting as desired.

       TBD: add support for stdlib detection
       TBD: should defaultdict be a set, not a list?
    """

    def __init__(self):
        self._distros_seen = defaultdict(list)  # _distros_seen[DISTRO_NAME] = [LIST_OF_SRC_FILES]

    def lookup(self, pathname):
        """  """
        dirpath, distname = distro_dir_and_name_from_src_filename(pathname)

        if dirpath is not None and distname is not None:  # if I found a distro owning it,

            if len(self._distros_seen[distname]) > 0 and dirpath not in self._distros_seen[distname]:
                print "ERROR: Seen distro in dir %r and %r" % (self._distros_seen[distname], dirpath)

            self._distros_seen[distname].append(dirpath)

        return dirpath, distname

class ImportOccurrences(object):
    """
    """

    class ImportOccurrence(object):
        """Information object collected about a single import operation.
        """

        is_imported = False
        is_used = False               # statically, after import is there code that actually uses it?
        is_actually_imported = False  # at runtime, is the import actually imported?
        is_dist_internal = False      # if import is to something within the same distribution

        imp_filename = None
        imp_distname = None

        def __init__(self, imp_modname, src_distname, src_filename, src_lineno):
            """
               imp_modname  -- name of module being imported
               src_distname -- name of distribution doing the import
               src_filename -- relpath to  src file doing the import
               src_lineno   -- line no  in src file doing the import

               imp_filename -- fullpath to module being imported
               imp_distname -- name of distribution being imported
               imp_dirpath  -- directory path to top of distribution
            """
            self.imp_modname  = imp_modname
            self.src_distname = src_distname
            self.src_filename = src_filename
            self.src_lineno   = src_lineno

    def __init__(self, distnames):
        self.distnames = distnames
        self.by_imp_modname  = defaultdict(list)  # lookup by name of package being imported
        self.by_src_filename = defaultdict(list)  # lookup by name of package doing the import
        self.by_src_lineno   = defaultdict(list)  # lookup by (file, lineno) of source file doing the import

    def record(self, imp_modname, src_filename, src_lineno,
               is_imported=None, is_used=None, is_actually_imported=None, is_dist_internal=None):

        src_dirpath, src_distname = self.distnames.lookup(src_filename)

        if src_distname is None:
            src_distname = src_filename

        if imp_modname is None:
            print "ERROR: imp_modname is None in record()"

        o = self.ImportOccurrence(imp_modname, src_distname, os.path.relpath(src_filename, src_dirpath), src_lineno)

        self.by_imp_modname[o.imp_modname].append(o)
        self.by_src_filename[o.src_filename].append(o)
        self.by_src_lineno[(o.src_filename, o.src_lineno)].append(o)

        if is_imported is not None:
            o.is_imported = is_imported

        if is_used is not None:
            o.is_used = is_used

        if is_actually_imported is not None:
            o.is_actually_imported = is_actually_imported

        if is_dist_internal is not None:
            o.is_dist_internal = is_dist_internal

        return o

    def report_unused_imports(self):
        """TBD: Break reports out into separate class/pgm.
        """

        info = []
        for imps in self.by_imp_modname.values():
            for imp in imps:
                if imp.is_used:
                    continue
                info.append((imp.src_distname, imp.src_filename, imp.src_lineno, imp.imp_modname))
        info = sorted(info)

        print "%d import occurrences unused" % (len(info), )

        # by pkgname:
        #   by srcfile:
        #      by lineno:
        #          modname imported but not used

        prev_distname, prev_src_filename, prev_src_lineno = object(), object(), object()
        for distname, src_filename, src_lineno, imp_modname in info:

            if distname != prev_distname:
                print "Unused Imports in Distribution: %s" % distname
                prev_distname = distname

            if src_filename != prev_src_filename:
                print "\n    %s" % src_filename
                prev_src_filename = src_filename

            if src_lineno != prev_src_lineno:
                print "        #%s" % src_lineno
                prev_src_lineno = src_lineno

            print "            ", imp_modname

            # make: Entering directory `/u/gnu/make'.
            # make: Leaving directory `/u/gnu/make'.

    def report_found_imports(self, options):
        """TBD: Break reports out into separate class/pgm.
        """

        info = []
        for imps in self.by_imp_modname.values():
            for imp in imps:
                info.append((imp.src_distname, imp.imp_modname, imp.imp_distname, imp))
        info = sorted(info)

        if options.ignore_stdlib:
            for src_distname, imp_modname, imp_distname, imp in info[:]:
                if imp_distname.startswith('stdlib'):
                    info.remove((src_distname, imp_modname, imp_distname, imp))

        if options.ignore_internal_imports:
            for src_distname, imp_modname, imp_distname, imp in info[:]:
                if src_distname == imp_distname:
                    info.remove((src_distname, imp_modname, imp_distname, imp))

        print "%d import occurrences found" % (len(info), )

        count = 0
        prev_distname, prev_imp_modname, prev_imp_distname, prev_imp = None, None, None, None
        for distname, imp_modname, imp_distname, imp in info:

            if distname != prev_distname:
                print "\nImports Made From Distribution: %s" % distname
                prev_distname = distname
                prev_imp_modname = None

            if imp_modname != prev_imp_modname:
                if prev_imp_modname is not None:
                    self._report_found_imports_line(count, prev_imp_modname, prev_imp_distname, prev_imp)

                prev_imp_modname  = imp_modname
                prev_imp_distname = imp_distname
                prev_imp          = imp

                count = 0

            count += 1

        else:  # on the last iteration, be sure to report on the last element
            if prev_imp_modname is not None:
                self._report_found_imports_line(count, prev_imp_modname, prev_imp_distname, imp)

    def _report_found_imports_line(self, count, imp_modname, imp_distname, imp):
        """TBD: Break reports out into separate class/pgm.
        """

        print "    %04d " % (count, ),
        print "%s " % (imp_modname, ),
        print "(%s)" % (imp_distname, ),

        if imp.is_used:
            print
        else:
            print "  [UNUSED]"

    def discover_unused_imports(self, pyfilename):
        """Using the 'pyflakes' tool, parse its output to discover unused imports.

           TBD: rec.compile should be a class/module-level var, not local!
        """

        # /home/jrush/JivaEggified/parts/pytest/site.py:746: WARNING 'sitecustomize' imported but unused
        patt = re.compile(r"""
            ^
            (?P<src_filename>.*\.py)        # full pathname to srcfile doing import
            :(?P<lineno>\d+):               # lineno within srcfile where import occurred
            \s
            '(?P<modname>[a-zA-Z0-9_]+)'    # name of module being imported
            \s
            imported\sbut\sunused
            $""", re.VERBOSE)

        def run(cmd, quiet=True):
            output = commands.getoutput(cmd)

            for line in output.splitlines():
                m = patt.match(line)
                if m:
                    yield m.group('modname'), m.group('src_filename'), m.group('lineno')

        for imp_modname, src_filename, src_lineno in run('pyflakes %s' % pyfilename):
            self.record(imp_modname, src_filename, src_lineno, is_imported=True, is_used=False)


class ImportsRunRecorder(object):
    """
    """

    def __init__(self, import_occurrences):
        """Hook into the module import mechanism."""

        self.import_occurrences = import_occurrences

    def __import__(self, modname, globals={}, locals={}, fromlist=[], level=-1):
        """
        """

        print "Importing: %s" % (modname, )

        m = self.old__import__(modname, globals, locals, fromlist, level)

        frame = sys._getframe(1)

        src_filename = inspect.getsourcefile(frame) or inspect.getfile(frame)  # src_filename,
        src_lineno = inspect.getframeinfo(frame)[1]                            # src_lineno

        o = self.import_occurrences.record(
            modname,
            src_filename,
            src_lineno,
            is_imported=True,
        )

        if hasattr(m, '__file__'):
            print "Module %r located at %r" % (modname, m.__file__)

            imp_dirpath, imp_distname = self.import_occurrences.distnames.lookup(m.__file__)

            o.imp_filename = m.__file__
            o.imp_dirpath  = imp_dirpath
            o.imp_distname = imp_distname
        else:
            print "Module %r has no __file__ attr" % (modname, )
            o.imp_distname = 'stdlib?'

        return m

    def run(self, cmdline):
        """  """

        self.old__import__ = sys.modules['__builtin__'].__import__
        sys.modules['__builtin__'].__import__ = self.__import__

        sys.argv = cmdline.split()
        try:
            with file(sys.argv[0]) as fh:
                exec fh
        except SystemExit:
            pass  # ignore exception caused by terminating target pgm

        sys.modules['__builtin__'].__import__ = self.old__import__


class ImportsAstRecorder(ast.NodeVisitor):
    """
    """

    distname_ignores = set((
    ))

    modname_ignores = set((
    ))

    src_filename = None  # name of .py performing the import operation
    pkgname = None

    def __init__(self, import_occurrences):
        self.import_occurrences = import_occurrences

    def visit(self, node, src_filename=None):
        """
        """

        if src_filename is not None:
            if self.src_filename != src_filename:
                self.pkgname = pkgname_from_src_filename(src_filename)
                print "====> pkgname set to %r" % (self.pkgname, )
            self.src_filename = src_filename

        return ast.NodeVisitor.visit(self, node)

    def visit_Import(self, node):
        """
        """

        print ast.dump(node, annotate_fields=True, include_attributes=True)

        for name in node.names:
            # self.modules_imported.add(self.visit(name))

            imp_modname = self.visit(name)
            print "visit_Import::imp_modname is %r, name is %r" % (imp_modname, name)

            self.import_occurrences.record(
                imp_modname,        # imp_modname
                self.src_filename,  # src_filename,
                node.lineno,        # src_lineno
                is_imported=True,
            )

    def visit_alias(self, node):
        """
        """

        print "visit_alias returning %r" % (node.name, )
        return node.name

    def visit_ImportFrom(self, node):
        """
        """

        ####
        # Convert relative import names e.g. "from .constants import alpha" into absolute.

        if node.level > 0:  # a relative import
            module = self.pkgname  # base on which relative applies
            addl_seg = '.' + node.module if node.module is not None else ''
            imp_modname = dottedname_uplevel(module, node.level) + addl_seg
        else:
            imp_modname = node.module  # an absolute import

        self.import_occurrences.record(
            imp_modname,
            self.src_filename,
            node.lineno,        # src_lineno
            is_imported=True,
        )


def imports():

    optsparser    = ImportsOptionParser()
    options, args = optsparser.parse_args()


    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    logger.addHandler(ch)


    topdir = args

    # 1) run pyflake over each .py file to determine unused imports
    # 2) parse ast of each .py file to determine names/places (not dirs) of imports
    # ?) run entire app, after patching pyenv, to refine dirs of imports
    # 4) report imports used
    # 5) report imports unused
    # ?) report imports never executed at all

    # option to ignore distname='stdlib' to/from
    # option to ignore internal imports
    # option to collapse imports into distnames and show which import which
    # reverse option to report who imports which distnames/modules

    distnames = DistributionNames()
    imports = ImportOccurrences(distnames)

    walker = ImportsAstRecorder(imports)

    # Do Static Analysis First and Accumulate Results

    for pyfilename in walktrees(rootdirs=topdir, filepatts=('*.py', ), recurse=True):
        if options.verbose:
            logger.info("EVALUATING: ", pyfilename)

        if options.unused_imports:
            imports.discover_unused_imports(pyfilename)

        if options.static_imports:
            with file(pyfilename) as f:
                tree = ast.parse(f.read(), filename=pyfilename)
                walker.visit(tree, src_filename=pyfilename)

    # Now Optionally Run Dynamic Analysis to Refine Information
    if options.run:
        walker = ImportsRunRecorder(imports)
        walker.run(options.run)
        imports.report_found_imports(options)

    if options.unused_imports:
        imports.report_unused_imports()

    if options.static_imports:
        imports.report_found_imports(options)
