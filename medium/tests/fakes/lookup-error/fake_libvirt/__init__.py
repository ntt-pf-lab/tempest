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
    def nwfilterLookupByName(instance_filter_name):
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


def fake_get_info_OK(self, instance_name):
    return {'state': 1,
                'max_mem': '2048',
                'mem': '1024',
                'num_cpu': '2',
                'cpu_time': '1'}


def libvirt_con_get_info_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection.get_info':
        return fake_get_info_OK
    else:
        return fn
