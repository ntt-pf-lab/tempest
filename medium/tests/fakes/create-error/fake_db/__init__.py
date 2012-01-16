import os
import time

from nova.db import api
from nova.db.sqlalchemy import api as sql_api
from nova.compute import task_states
from nova.compute import vm_states

#from storm import openstack
#import storm.config
#from storm import exceptions
import manager as ssh_manager
#import stackmonkey.manager as ssh_manager


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