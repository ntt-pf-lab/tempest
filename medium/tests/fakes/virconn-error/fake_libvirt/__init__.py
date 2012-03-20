import libvirt
from glance.common import exception as glance_exception


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


def fake_glance_show(self, context, image_id):
    raise glance_exception.ClientConnectionError


def libvirt_glance_show_patch(name, fn):
    if name == 'nova.image.glance.GlanceImageService.show':
        return fake_glance_show
    else:
        return fn


def fake_glance_show_not_found(self, context, image_id):
    raise glance_exception.NotFound


def libvirt_image_not_found_patch(name, fn):
    if name == 'nova.image.glance.GlanceImageService.show':
        return fake_glance_show_not_found
    else:
        return fn


def fake_glance_update(self, context, image_id, image_meta, data=None):
    raise glance_exception.ClientConnectionError


def libvirt_glance_update_patch(name, fn):
    if name == 'nova.image.glance.GlanceImageService.update':
        return fake_glance_update
    else:
        return fn


def fake_glance_update_notfound(self, context, image_id,
                                image_meta, data=None):
    raise glance_exception.NotFound


def libvirt_update_not_found_patch(name, fn):
    if name == 'nova.image.glance.GlanceImageService.update':
        return fake_glance_update_notfound
    else:
        return fn
