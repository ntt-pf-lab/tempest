import os
import libvirt


def openAuth(uri, auth, n):
    class fake(object):
        @staticmethod
        def defineXML(xml):
            class fake_domain(object):
                @staticmethod
                def createWithFlags(flag):
                    pass
            return fake_domain

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

        @staticmethod
        def lookupByName(instance_name):
            raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)

    return fake


def libvirt_patch(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth
    else:
        return fn
