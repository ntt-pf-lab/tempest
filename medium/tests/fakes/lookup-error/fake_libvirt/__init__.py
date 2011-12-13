import os
import libvirt


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


def openAuth(uri, auth, n):
    return fake


def libvirt_patch(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth
    else:
        return fn


class fake_no_domain(fake):
    @staticmethod
    def lookupByName(instance_name):
        raise libvirt.libvirtError(libvirt.VIR_ERR_NO_DOMAIN)


def openAuth_no_domain(uri, auth, n):
    return fake_no_domain


def libvirt_patch_no_domain(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_no_domain
    else:
        return fn
