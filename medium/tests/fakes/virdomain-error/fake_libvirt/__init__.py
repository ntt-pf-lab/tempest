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


def libvirt_patch_invalid_operation(name, fn):
    if name == 'libvirt.virDomain.undefine':
        return fake_undefine_invalid_operation
    else:
        return fn