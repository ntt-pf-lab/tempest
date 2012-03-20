import time

from nova.db import api
from nova.compute import task_states
from nova.compute import vm_states
from nova.virt import disk
from nova.virt import images
import libvirt
from nova import exception
from nova import image
from nova import log as logging

#from tempest import openstack
#import tempest.config
#from tempest import exceptions
import manager as ssh_manager
#import stackmonkey.manager as ssh_manager


LOG = logging.getLogger('log-for-fake-db')


def stopGlanceService():
    glance_havoc = ssh_manager.GlanceHavoc()
    glance_havoc.stop_glance_api()


def startLibvirtService():
    compute_havoc = ssh_manager.ComputeHavoc()
    compute_havoc._run_cmd("sudo service libvirt-bin start")

def stopLibvirtService():
    compute_havoc = ssh_manager.ComputeHavoc()
    compute_havoc._run_cmd("sudo service libvirt-bin stop")

def startDBService():
   havoc = ssh_manager.HavocManager()
   havoc._run_cmd("sudo service mysql start")


def stopDBService():
   havoc = ssh_manager.HavocManager()
   havoc._run_cmd("sudo service mysql stop")


def instance_get_stop(context, instance_id):
    stopDBService()
    return api.IMPL.instance_get(context, instance_id)


def db_stop_patch(name, fn):
    if name == 'nova.db.api.instance_get':
        return instance_get_stop
    else:
        return fn


def instance_get(context, instance_id):
    raise Exception
#    return api.IMPL.instance_get(context, instance_id)


def db_exception_patch(name, fn):
    if name == 'nova.db.api.instance_get':
        return instance_get
    else:
        return fn


def instance_type_get_stop(context, id):
    stopDBService()
    return api.IMPL.instance_type_get(context, id)


def db_type_stop_patch(name, fn):
    if name == 'nova.db.api.instance_type_get':
        return instance_type_get_stop
    else:
        return fn


def instance_type_get_exception(context, id):
    raise Exception


def db_type_exception_patch(name, fn):
    if name == 'nova.db.api.instance_type_get':
        return instance_type_get_exception
    else:
        return fn


def instance_update_stop(context, instance_id, updates):
    stopDBService()
    return api.IMPL.instance_update(context, instance_id, updates)


def instance_update_stop_patch(name, fn):
    if name == 'nova.db.api.instance_update':
        return instance_update_stop
    else:
        return fn


def instance_update_except(context, instance_id, updates):
    raise Exception


def instance_update_except_patch(name, fn):
    if name == 'nova.db.api.instance_update':
        return instance_update_except
    else:
        return fn


def compute_instance_update(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.BLOCK_DEVICE_MAPPING:
        stopDBService()
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_stop_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update
    else:
        return fn


def compute_instance_update_except(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.BLOCK_DEVICE_MAPPING:
        raise Exception
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_except_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update_except
    else:
        return fn


def compute_instance_update_stop_spawn(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.SPAWNING:
        stopDBService()
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_spawn_stop_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update_stop_spawn
    else:
        return fn


def compute_instance_update_except_spawn(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.SPAWNING:
        raise Exception
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_spawn_except_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update_except_spawn
    else:
        return fn


def compute_instance_update_stop_active(self, context, instance_id, **kwargs):
    if not kwargs['task_state'] and kwargs['vm_state'] == vm_states.ACTIVE:
        stopDBService()
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_active_stop_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update_stop_active
    else:
        return fn



def libvirt_create_image_ioerror(self, context, inst, libvirt_xml, suffix='',
                      disk_images=None, network_info=None,
                      block_device_info=None):
    raise IOError


def libvirt_create_image_ioerror_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._create_image':
        return libvirt_create_image_ioerror
    else:
        return fn


def libvirt_create_image_console_ioerror_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._create_image':
        return libvirt_create_image_ioerror
    else:
        return fn


def libvirt_fetch_image_stop_glance(self, context, target, image_id, user_id, project_id,
                     size=None):

#    if target.find('001') >= 0:
    stopGlanceService()
    images.fetch_to_raw(context, image_id, target, user_id, project_id)
    if size:
        disk.extend(target, size)


def libvirt_fetch_image_stop_glance_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._fetch_image':
        return libvirt_fetch_image_stop_glance
    else:
        return fn


def virt_images_fetch_href1(context, image_href, path, _user_id, _project_id):
    LOG.info('stop glance before get image_href:'+image_href)

    if image_href == '1':
        stopGlanceService()
    (image_service, image_id) = image.get_image_service(context,
                                                             image_href)
    try:
        with open(path, "wb") as image_file:
            metadata = image_service.get(context, image_id, image_file)
    except IOError:
        raise exception.InvalidDevicePath(path=path)
    return metadata


def libvirt_fetch_image_kerneldisk_stop_glance_patch(name, fn):
    if name == 'nova.virt.images.fetch':
        return virt_images_fetch_href1
    else:
        return fn


def virt_images_fetch(context, image_href, path, _user_id, _project_id):
    LOG.info('stop glance before get image_href:'+image_href)

    if image_href == '2':
        stopGlanceService()
    (image_service, image_id) = image.get_image_service(context,
                                                             image_href)
    try:
        with open(path, "wb") as image_file:
            metadata = image_service.get(context, image_id, image_file)
    except IOError:
        raise exception.InvalidDevicePath(path=path)
    return metadata


def libvirt_fetch_image_ramdisk_stop_glance_patch(name, fn):
    if name == 'nova.virt.images.fetch':
        return virt_images_fetch
    else:
        return fn


def virt_images_fetch_href3(context, image_href, path, _user_id, _project_id):
    LOG.info('stop glance before get image_href:'+image_href)

    if image_href == '3':
        stopGlanceService()
    (image_service, image_id) = image.get_image_service(context,
                                                             image_href)
    try:
        with open(path, "wb") as image_file:
            metadata = image_service.get(context, image_id, image_file)
    except IOError:
        raise exception.InvalidDevicePath(path=path)
    return metadata


def libvirt_fetch_image_rootdisk_stop_glance_patch(name, fn):
    print 'uuuuuuuu'+name
    if name == 'nova.virt.images.fetch':
        return virt_images_fetch_href3
    else:
        return fn


def libvirt_create_new_domain(self, xml, persistent=True, launch_flags=0):

    stopLibvirtService()

    if persistent:
        # To create a persistent domain, first define it, then launch it.
        domain = self._conn.defineXML(xml)

        domain.createWithFlags(launch_flags)
    else:
        # createXML call creates a transient domain
        domain = self._conn.createXML(xml, launch_flags)

    return domain


def create_domain_stop_libvirt_patch(name, fn):
    print 'uuuuuuuu'+name
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._create_new_domain':
        return libvirt_create_new_domain
    else:
        return fn


def libvirt_create_withflags(self, xml, persistent=True, launch_flags=0):

    if persistent:
        # To create a persistent domain, first define it, then launch it.
        domain = self._conn.defineXML(xml)

        stopLibvirtService()

        domain.createWithFlags(launch_flags)
    else:
        # createXML call creates a transient domain
        domain = self._conn.createXML(xml, launch_flags)

    return domain


def create_domain_withflags_stop_libvirt_patch(name, fn):
    print 'uuuuuuuu'+name
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._create_new_domain':
        return libvirt_create_withflags
    else:
        return fn


def libvirt_lookup_by_name(self, instance_name):

    stopLibvirtService()
    try:
        return self._conn.lookupByName(instance_name)
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_NO_DOMAIN:
            raise exception.InstanceNotFound(instance_id=instance_name)

        msg = _("Error from libvirt while looking up %(instance_name)s: "
                "[Error Code %(error_code)s] %(ex)s") % locals()
        raise exception.Error(msg)


def create_domain_lookup_stop_libvirt_patch(name, fn):
    print 'uuuuuuuu'+name
    if name == 'nova.virt.libvirt.connection.LibvirtConnection._lookup_by_name':
        return libvirt_lookup_by_name
    else:
        return fn






def compute_instance_update_excpt_active(self, context, instance_id, **kwargs):
    if not kwargs['task_state'] and kwargs['vm_state'] == vm_states.ACTIVE:
        raise Exception
    return api.IMPL.instance_update(context, instance_id, kwargs)


def compute_instance_update_active_except_patch(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return compute_instance_update_excpt_active
    else:
        return fn


def instance_get_and_stop_glance(context, instance_id):
    stopGlanceService()
    return api.IMPL.instance_get(context, instance_id)


def stop_glance_patch(name, fn):
    print 'yyyyyyyyyyyyyy'
    if name == 'nova.db.api.instance_get':
        return instance_get_and_stop_glance
    else:
        return fn

def show_glance(self, context, image_id):
    print 'pppppppppp'

    cnt = 0
    while cnt < 60:
        cnt += 1
        time.sleep(10)

    raise Exception


def wait_glance_patch(name, fn):
    print 'yyyyyyyyyyyyyy' +  name
    if name == 'nova.image.glance.GlanceImageService.show':
        return show_glance
    else:
        return fn
