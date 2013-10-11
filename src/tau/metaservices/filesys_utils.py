######################################################################
# Copyright 2013 Tau Productions Inc. by Jeff Rush

"""
"""

import logging
import os
import types

from fnmatch import fnmatch

log = logging.getLogger('tau.metaservices')


def walktrees(rootdirs, filepatts=None, recurse=False):
    """Walk one (or more) directory trees, yielding paths to matching filenames.

       This function extends to os.walk() function in the standard library by:

       1) walking a list of directory trees, not just one tree
       2) skipping over Subversion and Git hidden directories
       3) following symbolic links, since they are used in buildouts for developer eggs
       4) only returns files, not directories
       5) matches against filename patterns
    """

    if rootdirs is None:            # if not given a set of root directories to traverse,
        rootdirs = (os.getcwd(), )  #   just traverse the current working directory

    if isinstance(rootdirs, types.StringTypes):
        rootdirs = (rootdirs, )     # if given a string, make it a list of (one) string

    if isinstance(filepatts, types.StringTypes):
        filepatts = (filepatts, )   # if given a string, make it a list of (one) string

    for rootdir in rootdirs:
        if not os.path.isdir(rootdir):
            raise IOError("ERROR: Root directory %r is NOT actually a directory!" % rootdir)

        for dirpath, dirnames, filenames in os.walk(rootdir, followlinks=True):

            if '.svn' in dirnames:  # do not descend into .svn directories
                dirnames.remove('.svn')
            if '.git' in dirnames:  # do not descend into .git directories
                dirnames.remove('.git')

            for filename in filenames:

                if filepatts is None:
                    full_filename = os.path.join(dirpath, filename)
                    yield full_filename
                else:
                    for filepatt in filepatts:
                        if fnmatch(filename, filepatt):
                            full_filename = os.path.join(dirpath, filename)
                            yield full_filename

            if not recurse:
                break


def pkgname_from_src_filename(src_filename):
    """Given path to a srcfile or dir, ascend directories and return its dotted package name.

       Note that a package name is NOT the same as a distribution name, or the
       egg from which it came.  A distribution may contain multiple packages,
       or the srcfile may be in the standard library, which isn't a
       distribution/egg.
    """

    if os.path.isfile(src_filename):
        # discard trailing .py filename, keeping only dirname
        pathname, src_filename = os.path.split(src_filename)
    else:
        pathname = src_filename

    pathname = os.path.abspath(pathname)

    module_segments = []  # accumulate intermediate module names as we ascend from a srcfile
    while pathname != '/':
        log.debug("Seeking PackageName for pathname=%r", pathname)

        if os.path.isdir(pathname):
            testname = os.path.join(pathname, '__init__.py')
            if os.path.isfile(testname):  # found a directory with an __init__.py file
                _, segment = os.path.split(pathname)
                module_segments.append(segment)
            else:
                return '.'.join(reversed(module_segments))

        pathname, _ = os.path.split(pathname)  # ascend by stripping off a level of child-directory

    return [os.path.splitext(src_filename)[0]]  # not part of a package, just return the module name


def distro_dir_and_name_from_src_filename(src_filename):
    #def dirpath_and_distname(pathname):
    """Give path to a srcfile, egg or directory, return its distribution directory and name.
    """
    pathname = src_filename  # keep original 'src_filename' value intact

    pathname = os.path.abspath(pathname)  # convert partial names to full names

    while pathname != '/':
        log.debug("DistributionName, pathname=%r", pathname)

        ####
        # To support the omelette recipe for buildout, which creates a
        # map, using symlinks, to all source used in a project, follow any
        # symlinks I find.

        if os.path.islink(pathname):
            pathname = os.readlink(pathname)
            log.debug("DistributionName, found symlink, switching to %r", pathname)

        ####
        # To support buildout-cached eggs which unzips them, detect a
        # file/directory name that ends with '.egg'.  If so, extract the
        # distribution name from that directory name.

        if pathname.endswith('.egg'):
            pathname, eggname = os.path.split(pathname)
            log.debug("Found Distribution: %s", eggname.split('-', 1)[0])
            return pathname, eggname.split('-', 1)[0]

        ####
        # To support the case of a development egg with a
        # <DISTRIBUTION>.egg-info directory, as I ascend the directory
        # hierarchy, look sideways to see if such a '*.egg-info' directory
        # exists.

        if os.path.isdir(pathname):
            names = os.listdir(pathname)
            infodirs = [name for name in names if name.endswith('.egg-info')]
            if infodirs:
                infodir = infodirs[0]  # assume there is only one
                if os.path.isdir(os.path.join(pathname, infodir)):
                    distname = infodir[:-len('.egg-info')]
                    log.debug("Found Distribution %s in Directory %s", distname, pathname)
                    return pathname, distname

        ####
        # Finally detect if pathname is pointing into the Python Standard Library.

        if os.path.isfile(os.path.join(pathname, '__future__.py')):
            return pathname, "stdlib"

        pathname, _ = os.path.split(pathname)  # ascend by stripping off a level of directory

    return os.path.split(src_filename)[0], 'extralib'  # not an egg of any kind, nor in the standard library


def dottedname_uplevel(name, levels):
    """
    """
    levels -= 1

    paths = name.split('.')
    paths = paths[:-levels] if levels > 0 else paths[:]

    return '.'.join(paths)
