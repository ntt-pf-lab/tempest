import os
import libvirt


def fake_defineXML(self, xml):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_definexml_patch(name, fn):
    if name == 'libvirt.virConnect.defineXML':
        return fake_defineXML
    else:
        return fn


def fake_get_info(self, instance_name):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_con_get_info_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection.get_info':
        return fake_get_info
    else:
        return fn
