#!/bin/env python2.7
"""
"""
#!/bin/env python2.7     # TBD: solve this problem

import re
import os
import ast
import logging

from os.path import splitext
from optparse import OptionParser
from collections import defaultdict

from filesys_utils import (
    walktrees,
    pkgname_from_src_filename,
)

logger = logging.getLogger('tplmapper')


class TemplatesOptionParser(OptionParser):
    """
    """

    usage = "usage: %prog [options]"

    def __init__(self, **kw):
        OptionParser.__init__(self, **kw)

        self.add_option("-n", "--dry-run",
                        action="store_true", dest="dry_run", default=False,
                        help="skip any changes to files, just report results")

        self.add_option("-v", "--verbose",
                        action="store_true", dest="verbose", default=False,
                        help="show details of problems, not just summary counts")

        self.add_option("--templates-invoked",
                        action="store_true", dest="templates_invoked", default=False,
                        help="report use of DTML templates by controller methods")

        self.add_option("-u", "--unused-templates",
                        action="store_true", dest="unused_templates", default=False,
                        help="report imports statically found in source that are never used in the code")

        self.add_option("--run",
                        action="store", dest="run", default=None,
                        help="hook import machinery and run this program to see what gets imported.")


        #class DtmlTemplateUsageRecorder(ast.NodeVisitor):
        #
        #    distname = None
        #
        #    def __init__(self, dtml_collection):
        #        self.dtml_collection = dtml_collection
        #
        #    def visit(self, node, distname=None, filename=None):
        #        if distname is not None:
        #            self.distname = distname
        #        self.filename = filename
        #        print "Visiting Package: %s (%s)" % (self.distname, self.filename)
        #        ast.NodeVisitor.visit(self, node)
        #
        #    def visit_Module(self, node):
        #        self.generic_visit(node)        # descend into the Module's subtree
        #
        #    def visit_Name(self, node):
        #        print "Name: %r" % (node.id, )
        #
        #    def visit_NameConstant(self, node):
        #        print "NameConstant: %r" % (node.id, )
        #
        #    def visit_Str(self, node):
        #        print "Str: %r" % (node.s, )
        #
        #        if node.s in self.dtml_collection:
        #            print "DTML basename %r found in source code" % (node.s, )
        #            self.dtml_collection.mark_used(node.s, node.lineno, ??)


class DtmlTemplates(object):
    """Internal representation of a collecton of DTML Template file.
    """

    class DtmlTemplate(object):
        """Internal representation about a DTML Template file.
        """

        def __init__(self, fullname):
            self.fullname = fullname
            self.pathname, self.filename = os.path.split(fullname)
            self.basename = splitext(self.filename)[0]

            self.patt_basename = re.compile(r"['\"]%s['\"]" % (self.basename, ))

            # self.used[srcfile] = (linenos, )
            self.used          = defaultdict(set)

            # self.greps[srcfile] = (linenos, )
            self.greps         = defaultdict(set)

    def __init__(self):
        self.tpls = {}

    def load(self, topdirs):
        """Load information about all DTML templates found under a directory tree.
        """

        for filename in walktrees(topdirs, suffixes=('.dtml', ), recurse=True):
            t = self.DtmlTemplate(filename)
            self.tpls[t.basename] = t

        print "Identified %d .dtml files" % len(self.tpls)
        for tpl_basename, tpl_obj  in self.tpls.items():
            print tpl_basename

    def __contains__(self, basename):
        return basename in self.tpls

    def mark_used(self, basename, lineno, pysrcfilename):
        self.tpls[basename].used[pysrcfilename].add(lineno)

    def mark_greps(self, basename, lineno, pysrcfilename):
        self.tpls[basename].greps[pysrcfilename].add(lineno)

    def grep_for_unused_templates(self, pysrc, pysrcfilename):
        """  """

        for lineno, linetext in enumerate(pysrc.split('\n')):
            for tpl in self.tpls.values():
                if not tpl.used:
                    m = tpl.patt_basename.search(linetext)
                    if m:
                        print "Found %r at line# %d in file %s" % (
                            tpl.basename, lineno+1, pysrcfilename)

                        self.mark_greps(tpl.basename, lineno+1, pysrcfilename)

    def report_unused_templates(self):
        """  """

        templates = self.tpls.values()
        templates = sorted(templates, key=lambda template: template.fullname)

        tgt = [tpl for tpl in templates if not tpl.used and not tpl.greps]
        title = "%d Definitely Unused Templates" % len(tgt)
        title += '\n' + '-'*len(title)

        longest_basename = max(tgt, key=lambda template: len(template.basename)).basename
        print "%d" % (len(longest_basename), )
        fmt_str = "  %%-%ds %%s" % (len(longest_basename), )

        print "\n", title
        for tpl in tgt:
            print fmt_str % (tpl.basename, tpl.pathname, )


        tgt = [tpl for tpl in templates if not tpl.used and tpl.greps]
        title = "%d Possibly Unused Templates" % len(tgt)
        title += '\n' + '-'*len(title)

        longest_basename = max(tgt, key=lambda template: len(template.basename)).basename
        print "%d" % (len(longest_basename), )
        fmt_str = "  %%-%ds %%s" % (len(longest_basename), )

        print "\n", title

        for tpl in tgt:
            print fmt_str % (tpl.basename, tpl.pathname, )

            for srcfilename, linenos in tpl.greps.items():
                print "    ", srcfilename, linenos

    #TBD: add code to tag .dtml entry with the distname it came from


class TemplateReferenceAstRecorder(ast.NodeVisitor):

    distname_ignores = set((
    ))

    modname_ignores = set((
    ))

    src_filename = None  # name of .py file making the reference to a template
    pkgname = None
    classname = None
    funcname = None
    callname = None

    def __init__(self, dtml_templates):
        self.dtml_templates = dtml_templates
        self.attrpath = []

    def visit(self, node, src_filename=None):
        if src_filename is not None:
            if self.src_filename != src_filename:
                self.pkgname = pkgname_from_src_filename(src_filename)
                print "====> pkgname set to %r" % (self.pkgname, )
                self.src_filename = src_filename

        return ast.NodeVisitor.visit(self, node)

    def visit_ClassDef(self, node):
        """Wrap the Nested Body of a Class Definition"""
        self.classname = node.name

        print "Class: %s" % (self.classname, )

        rc = ast.NodeVisitor.generic_visit(self, node)

        self.classname = None
        return rc

    def visit_FunctionDef(self, node):
        """Wrap the Nested Body of a Function/Method Definition"""
        self.funcname = node.name

        if self.classname is None:
            print "Function: %s" % (self.funcname, )
        else:
            print "Method: %s in class %s" % (self.funcname, self.classname)

            #        if self.funcname == 'getSentinelLogLeftNav':
        if self.funcname == 'showActionPageForAssessment':
            print ast.dump(node, annotate_fields=True, include_attributes=True)

        rc = ast.NodeVisitor.generic_visit(self, node)
        self.funcname = None
        return rc

    def visit_Attribute(self, node):
        """ handles VARNAME.ATTRNAME2 or varname.ATTRNAME1.ATTRNAME2 attribute lookup

            dtml_document = getattr(self.views, 'ace_action')     # line 251, showActionPageForAssessment
            dtml_document = self.views.sentinel_left_navigation   # line 590, getSentinelLogLeftNav
        """

        if not isinstance(node, ast.Attribute):
            return None  # attribute name is not a string literal but a variable

        if isinstance(node, ast.Attribute):
            self.attrpath.insert(0, node.attr)  # prepend the attribute we are currently looking at
        else:
            self.attrpath.insert(0, None)  # prepend the attribute we are currently looking at

        if isinstance(node.value, ast.Name):  # if reached the top-most var i.e. self.ATTRNAME

            # print "Prepending Name %r to attrpath %r, for lineno %d" % (
            #     node.value.id, self.attrpath, node.lineno)
            self.attrpath.insert(0, node.value.id)

            # print "attrpath is now %s" % ('.'.join(self.attrpath), )
            rc = ast.NodeVisitor.generic_visit(self, node)

            apath = '.'.join(self.attrpath)
            if apath.startswith('self.views.'):
                self.referencing_template(self.attrpath[2], node.lineno)

            # print "before pop #1 of 2, attrpath is %s" % (self.attrpath, )
            self.attrpath.pop(0)
            # print "before pop #2 of 2, attrpath is %s" % (self.attrpath, )
            self.attrpath.pop(0)

            return apath

        rc = ast.NodeVisitor.generic_visit(self, node)
        self.attrpath.pop(0)  # remove the attribute we were currently looking at
        return rc

    def visit_Call(self, node):
        """  """
        if isinstance(node.func, ast.Name):
            self.callname = node.func.id

        #  rc = ast.NodeVisitor.generic_visit(self, node)

        if self.callname == 'getattr':
            nargs = len(node.args)
            print "Calling %s w/%d args, lineno %d" % (self.callname, nargs, node.lineno)

            arg1 = self.visit_Attribute(node.args[0])
            if arg1 == 'self.views':
                if isinstance(node.args[1], ast.Str):
                    arg2 = node.args[1].s
                else:
                    print "ERROR: Cannot determine name of template being referenced in lineno %d!" % (node.lineno, )
                    arg2 = None

                print "Calling %s(%s, %r) at lineno %d" % (self.callname, arg1, arg2, node.lineno)
                self.referencing_template(arg2, node.lineno)

        self.callname = None

    def referencing_template(self, basename, lineno):
        """  """
        print "----> Ref to Template: %s, lineno %d" % (basename, lineno)

        if basename in self.dtml_templates:
            self.dtml_templates.mark_used(basename, lineno, self.src_filename)
        else:
            print "ERROR: Template %r referenced but not found as .dtml file." % (basename, )


"""
#250    request = self.REQUEST
#251    dtml_document = getattr(self.views, 'ace_action')

    Assign(
      targets=[
        Name(id='dtml_document', ctx=Store())
      ],
      value=Call(
        func=Name(id='getattr', ctx=Load()),
        args=[
          Attribute(value=Name(id='self', ctx=Load()),
                    attr='views', ctx=Load()),
          Str(s='ace_action')
        ],
        keywords=[], starargs=None, kwargs=None),
      )



#589    REQUEST = self.REQUEST
#590    dpage = self.views.sentinel_left_navigation
#591    return dpage(self.views, REQUEST=self.REQUEST,tag_name='log')


FunctionDef(
    name='getSentinelLogLeftNav',
    args=arguments(args=[
      Name(id='self', ctx=Param(), lineno=584, col_offset=30)
    ],
    vararg=None,
    kwarg=None,
    defaults=[]),

    body=[

      Assign(
        targets=[
          Name(id='dpage', ctx=Store())
        ],
        value=Attribute(value=Attribute(value=Name(id='self', ctx=Load()),
                                        attr='views', ctx=Load()),
                        attr='sentinel_left_navigation', ctx=Load()
        ),
      ),
"""





def tplmapper():
    optsparser = TemplatesOptionParser()
    options, args = optsparser.parse_args()

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    logger.addHandler(ch)

    topdir = args

    # 1) walk filesystem and locate every .dtml file
    # 2) parse ast of each .py file to detect invocations of each .dtml file

    dtml_templates = DtmlTemplates()  # a place to collect information about DTML templates
    dtml_templates.load(topdir)       # locate and make note of every DTML file found

    # dpage = self.views.SOME_TEMPLATE_NAME

    walker = TemplateReferenceAstRecorder(dtml_templates)

    for pyfilename in walktrees(rootdirs=topdir, filepatts=('*.py', ), recurse=True):
        if options.verbose:
            logger.info("EVALUATING: ", pyfilename)

        with file(pyfilename) as f:

            if 'ZeSentinelCtrl.py' in pyfilename:
                pysrc = f.read()
                tree = ast.parse(pysrc, filename=pyfilename)
                walker.visit(tree, src_filename=pyfilename)

                dtml_templates.grep_for_unused_templates(pysrc, pyfilename)

    if options.unused_templates:
        dtml_templates.report_unused_templates()
