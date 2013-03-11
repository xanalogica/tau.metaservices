import sys
import ihooks
import inspect
import fnmatch
import logging

from types import ModuleType

class MetaServices(ihooks.Hooks):
    """Collection of useful metaprogramming hooks and methods."""

    def __init__(self):
        ihooks.Hooks.__init__(self)
        self.import_subclasses = {}  # pre-import: mapping of modules to replacement classes
        self.import_watchers = {}    # post-import: mapping of modules to adjustment functions

        self.loader = ihooks.FancyModuleLoader(hooks=self)
        self.importer = ihooks.ModuleImporter(self.loader)

    def __import__(self, modname, globals={}, locals={}, fromlist=[], level=-1):

        logging.debug("Wish to import module %r" % (modname, ))
        if modname in self.import_subclasses:
            mod_cls = self.import_subclasses[modname]
            logging.debug("Remapping module to a subclass")

            class SubclassingHooks(ihooks.Hooks):
                def new_module(self, name):
                    logging.debug("Given %r, returning a %r instead of a %r" % (name, mod_cls, ModuleType))
                    return mod_cls(name)   # instead of imp.new_module(name)

            loader = ihooks.FancyModuleLoader(hooks=SubclassingHooks())
            importer = ihooks.ModuleImporter(loader)
        else:
            importer = self.importer
            logging.debug("NOT Remapping module to a subclass")

        m = importer.import_module(modname, globals, locals, fromlist)
        logging.debug("Import module %r of type %r" % (modname, type(m)))

        if modname in self.import_watchers: # call post-import handlers
            callfunc, filepatt = self.import_watchers[modname]

            frame = sys._getframe(1)
            importing_file = inspect.getsourcefile(frame) or inspect.getfile(frame)

            logging.debug(importing_file)

            if filepatt is None or fnmatch.fnmatch(importing_file, filepatt):
                m = callfunc(m) or m

        return m

    def subclass_module(self, modname, cls):
        if sys.modules['__builtin__'].__import__ != self.__import__:
            sys.modules['__builtin__'].__import__ = self.__import__  # hook __import__ operation

        logging.debug("Adding mapping of modulename %r to class %r" % (modname, cls))
        self.import_subclasses[modname] = cls

    def call_after_import_of(self, modname, callfunc, from_filepatt=None):

        if sys.modules['__builtin__'].__import__ != self.__import__:
            sys.modules['__builtin__'].__import__ = self.__import__  # hook __import__ operation

        self.import_watchers[modname] = (callfunc, from_filepatt)
