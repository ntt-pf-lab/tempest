import os
import re
import subprocess
import tempfile
import time
import stackmonkey.manager as ssh_manager


def cleanup_virtual_instances():
    # kill still existing virtual instances.
    for line in subprocess.check_output('virsh list --all',
                                        shell=True).split('\n')[2:-2]:
        line = line.strip()
        (id, name, state) = re.split('\s+', line, maxsplit=2)
        if state == 'running':
            subprocess.check_call('virsh destroy %s' % id, shell=True)
        subprocess.check_call('virsh undefine %s' % name, shell=True)


def cleanup_processes(processes):
    for process in processes:
        process.stop()
    lambda: time.sleep(10)


def emphasised_print(s, decorator='*-'):
    print(decorator * 100)
    print('')
    print(s)
    print('')
    print(decorator * 100)


def silent_check_call(*args, **kwargs):
    fake_stdout = tempfile.TemporaryFile()
    fake_stderr = tempfile.TemporaryFile()
    try:
        for (name, file) in [('stdout', fake_stdout),
                             ('stderr', fake_stderr)]:
            if name not in kwargs:
                kwargs[name] = file
        subprocess.check_call(*args, **kwargs)
    except subprocess.CalledProcessError:
        fake_stdout.seek(0)
        fake_stderr.seek(0)
        emphasised_print("STDOUT result:\n\n" + fake_stdout.read())
        emphasised_print("STDERR result:\n\n" + fake_stderr.read())
        raise


def startDBService():
    havoc = ssh_manager.HavocManager()
    havoc._run_cmd("sudo service mysql start")


def stopDBService():
    havoc = ssh_manager.HavocManager()
    havoc._run_cmd("sudo service mysql stop")


def checkDBService():
    havoc = ssh_manager.HavocManager()
    return havoc._run_cmd("sudo service mysql status")


def exist_vm_in_virsh(vm_id):
    for line in subprocess.check_output('virsh list --all',
                                        shell=True).split('\n')[2:-2]:
        (id, name, state) = line.split(None, 2)
        if id == str(vm_id):
            return True
    else:
        return False


def get_vm_state_in_virsh(vm_id):
    for line in subprocess.check_output('virsh list --all',
                                        shell=True).split('\n')[2:-2]:
        (id, name, state) = line.split(None, 2)
        if id == str(vm_id):
            return state
    else:
        raise Exception('VM could not be found by virsh.')


def _exec_sql(config, sql, db):
    exec_sql = 'mysql -u %s -p%s -h%s %s -Ns -e "' + sql + '"'
    results = subprocess.check_output(exec_sql
                                      % (config.mysql.user,
                                         config.mysql.password,
                                         config.mysql.host,
                                         db),
                                      shell=True)
    return [tuple(result.split('\t'))
                for result in results.split('\n') if result]


def _get_instance_in_db(config, id):
    sql = 'select id, vm_state, power_state, task_state, deleted '\
          'from instances where id = %s;' % str(id)
    return _exec_sql(config, sql, db='nova')


def _get_vif_in_db(config, id):
    sql = 'select id, instance_id, network_id, address, deleted '\
          'from virtual_interfaces where id = %s;' % str(id)
    return _exec_sql(config, sql, db='nova')


def _get_image_in_db(config, id):
    sql = 'select id, status, deleted, name, is_public, disk_format, '\
          'container_format, location from images where id = %s;' % str(id)
    return _exec_sql(config, sql, db='glance')


def _get_image_id_by_image_name_in_db(config, image_name):
    sql = 'select id from images where name = \'%s\' '\
          'order by created_at desc;' % image_name
    results = _exec_sql(config, sql, db='glance')
    if not results:
        return None

    return results[0][0]


def exist_instance_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if results:
        return True
    else:
        return False


def get_instance_vm_state_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if not results:
        raise Exception('VM could not be found in DB.')

    return results[0][1]


def get_instance_power_state_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if not results:
        raise Exception('VM could not be found in DB.')

    return results[0][2]


def get_instance_task_state_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if not results:
        raise Exception('VM could not be found in DB.')

    return results[0][3]


def get_instance_deleted_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if not results:
        raise Exception('VM could not be found in DB.')

    return results[0][4]


def exist_vif_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if results:
        return True
    else:
        return False


def get_vif_instance_id_in_db(config, id):
    results = _get_instance_in_db(config, id)
    if not results:
        raise Exception('VM could not be found in DB.')

    return results[0][1]


def exist_image_in_db(config, id):
    results = _get_image_in_db(config, id)
    if results:
        return True
    else:
        return False


def get_image_status_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][1]


def get_image_deleted_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][2]


def get_image_name_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][3]


def get_image_is_public_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][4]


def get_image_disk_format_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][5]


def get_image_container_format_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][6]


def get_image_location_in_db(config, id):
    results = _get_image_in_db(config, id)
    if not results:
        raise Exception('Image could not be found in DB.')

    return results[0][7]


def get_image_id_by_image_name_in_db(config, image_name):
    image_id = _get_image_id_by_image_name_in_db(config, image_name)
    if not image_id:
        raise Exception('Image could not be found in DB.')

    return int(image_id)

def _id_to_instance_id(id, template='instance-%08x'):
    """Convert an ID (int) to an instance ID (instance-[base 16 number])"""
    return template % id


def exist_instance_path(config, id):
    instance_name = _id_to_instance_id(int(id))
    instance_path = os.path.join(config.nova.directory,
                                 'instances', instance_name)
    return os.path.exists(instance_path)


def exist_image_path(config, id):
    image_path = os.path.join(config.glance.directory, 'images', str(id))
    return os.path.exists(image_path)
