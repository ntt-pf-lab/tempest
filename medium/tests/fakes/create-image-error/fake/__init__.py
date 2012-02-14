import os
import time
import subprocess

from nova.db import api
from nova.db.sqlalchemy import api as sql_api
from nova.compute import task_states

import manager as ssh_manager


def stopGlanceService():
    glance_havoc = ssh_manager.GlanceHavoc()
    glance_havoc.stop_glance_api()
    time.sleep(10)


def startDBService():
    havoc = ssh_manager.HavocManager()
    havoc._run_cmd("sudo service mysql start")


def stopDBService():
    havoc = ssh_manager.HavocManager()
    havoc._run_cmd("sudo service mysql stop")


def stopLibvirtService():
    havoc = ssh_manager.HavocManager()
    compute_havoc = ssh_manager.ComputeHavoc()
    compute_havoc.stop_libvirt()
    time.sleep(10)


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


def db_exception_patch(name, fn):
    if name == 'nova.db.api.instance_get':
        return instance_get
    else:
        return fn


def instance_update_stop_at_first_update(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.IMAGE_SNAPSHOT:
        stopDBService()
    return api.IMPL.instance_update(context, instance_id, kwargs)


def instance_update_stop_patch_at_first_update(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return instance_update_stop_at_first_update
    else:
        return fn


def instance_update_except_at_first_update(self, context, instance_id, **kwargs):
    if kwargs['task_state'] == task_states.IMAGE_SNAPSHOT:
        raise Exception
    return api.IMPL.instance_update(context, instance_id, kwargs)


def instance_update_except_patch_at_first_update(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return instance_update_except_at_first_update
    else:
        return fn


def instance_update_stop_at_last_update(self, context, instance_id, **kwargs):
    if kwargs['task_state'] is None:
        stopDBService()
    return api.IMPL.instance_update(context, instance_id, kwargs)


def instance_update_stop_patch_at_last_update(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return instance_update_stop_at_last_update
    else:
        return fn


def instance_update_except_at_last_update(self, context, instance_id, **kwargs):
    if kwargs['task_state'] is None:
        raise Exception
    return api.IMPL.instance_update(context, instance_id, kwargs)


def instance_update_except_patch_at_last_update(name, fn):
    if name == 'nova.compute.manager.ComputeManager._instance_update':
        return instance_update_except_at_last_update
    else:
        return fn


def virtual_interface_get_by_instance_stop(context, instance_id):
    stopDBService()
    return api.IMPL.virtual_interface_get_by_instance(context, instance_id)


def virtual_interface_get_by_instance_stop_patch(name, fn):
    if name == 'nova.db.api.virtual_interface_get_by_instance':
        return virtual_interface_get_by_instance_stop
    else:
        return fn


def virtual_interface_get_by_instance_except(context, instance_id):
    raise Exception


def virtual_interface_get_by_instance_except_patch(name, fn):
    if name == 'nova.db.api.virtual_interface_get_by_instance':
        return virtual_interface_get_by_instance_except
    else:
        return fn


def instance_get_libvirt_stop(context, instance_id):
    stopLibvirtService()
    return api.IMPL.instance_get(context, instance_id)


def instance_get_libvirt_stop_patch(name, fn):
    if name == 'nova.db.api.instance_get':
        return instance_get_libvirt_stop
    else:
        return fn


def virtual_interface_get_by_instance_libvirt_stop(context, instance_id):
    stopLibvirtService()
    return api.IMPL.instance_get(context, instance_id)


def virtual_interface_get_by_instance_libvirt_stop_patch(name, fn):
    if name == 'nova.db.api.virtual_interface_get_by_instance':
        return virtual_interface_get_by_instance_libvirt_stop
    else:
        return fn


def shutil_rmtree_libvirt_stop(path, ignore_errors=False, onerror=None):
    stopLibvirtService()


def shutil_rmtree_libvirt_stop_patch(name, fn):
    if name == 'shutil.rmtree':
        return shutil_rmtree_libvirt_stop
    else:
        return fn
