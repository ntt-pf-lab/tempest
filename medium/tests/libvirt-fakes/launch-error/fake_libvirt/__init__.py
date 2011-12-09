import os

import libvirt


def openAuth(uri, auth, n):
    class fake(object):
        @staticmethod
        def defineXML(xml):
            raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)

        @staticmethod
        def listDomainsID():
            return []

        @staticmethod
        def getCapabilities():
            return file(os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            'capabilities.xml')).read()

        @staticmethod
        def getType():
            return 'qemu'

        @staticmethod
        def getVersion():
            return '12003'

        @staticmethod
        def nwfilterDefineXML(xml):
            pass

    return fake


def libvirt_patch(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth
    else:
        return fn
