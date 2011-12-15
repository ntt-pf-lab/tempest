import os
import libvirt


def fake_destroy(conn):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_patch(name, fn):
    if name == 'libvirt.virDomain.destroy':
        return fake_destroy
    else:
        return fn


def fake_destroy_invalid_operation(conn):
    raise libvirt.libvirtError(libvirt.VIR_ERR_OPERATION_INVALID)


def libvirt_patch_invalid_operation(name, fn):
    if name == 'libvirt.virDomain.destroy':
        return fake_destroy_invalid_operation
    else:
        return fn


def fake_undefine(conn):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_patch_undefine(name, fn):
    if name == 'libvirt.virDomain.undefine':
        return fake_undefine
    else:
        return fn


def fake_undefine_invalid_operation(conn):
    raise libvirt.libvirtError(libvirt.VIR_ERR_OPERATION_INVALID)


def libvirt_undefine_patch_invalid_operation(name, fn):
    if name == 'libvirt.virDomain.undefine':
        return fake_undefine_invalid_operation
    else:
        return fn


def fake_createWithFlags(self, flags):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_create_patch(name, fn):
    if name == 'libvirt.virDomain.createWithFlags':
        return fake_createWithFlags
    else:
        return fn


def fake_snapshotCreateXML(self, xmlDesc, flags):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_snap_createxml_patch(name, fn):
    if name == 'libvirt.virDomain.snapshotCreateXML':
        return fake_snapshotCreateXML
    else:
        return fn


def fake_XMLDesc(self, flags):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_snap_xmldesc_patch(name, fn):
    if name == 'libvirt.virDomain.XMLDesc':
        return fake_XMLDesc
    else:
        return fn


def fake_delete(self, flags):
    raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def libvirt_snap_delete_patch(name, fn):
    if name == 'libvirt.virDomainSnapshot.delete':
        return fake_delete
    else:
        return fn
