import sys
import logging

from tau.metaservices import MetaServices

def test_postimport():
    from dummy_replacements import ReplacementRequest

    ms = MetaServices()

    def adjust(mod): # function to modify the target module before it is used
        mod.Request = ReplacementRequest

    ms.call_after_import_of('dummy_webapp', adjust)

    from dummy_webapp import HTTPServer
    hs = HTTPServer()

    assert isinstance(hs.handle_request(), ReplacementRequest)

def test_preimport():
    from types import ModuleType
    from dummy_replacements import ReplacementRequest


    ms = MetaServices()

    class ModuleWatcher(ModuleType):

        def __init__(self, modname):
            self.modname = modname

        def __getattribute__(self, name):
            modname = ModuleType.__getattribute__(self, 'modname')
            logging.info(".......... fetching attr %r of module %r" % (name, modname))

            if name == 'Request':
                return ReplacementRequest
            else:
                return ModuleType.__getattribute__(self, name)

    ms.subclass_module('dummy_request', ModuleWatcher)

    from dummy_webapp import HTTPServer
    hs = HTTPServer()

    assert isinstance(hs.handle_request(), ReplacementRequest)
