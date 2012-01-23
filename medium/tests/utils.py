import re
import subprocess
import tempfile
import time


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
    exec_sql = 'mysql -u %s -p%s %s -Ns -e "' + sql + '"'
    results = subprocess.check_output(exec_sql
                                      % (config.mysql.user,
                                         config.mysql.password,
                                         db),
                                      shell=True)
    return [tuple(result.split('\t'))
                for result in results.split('\n') if result]


def _get_instance_in_db(config, id):
    sql = 'select id, vm_state, power_state, task_state, deleted '\
          'from instances where id = %s;' % id
    return _exec_sql(config, sql, db='nova')


def _get_vif_in_db(config, id):
    sql = 'select id, instance_id, network_id, address, deleted '\
          'from virtual_interfaces where id = %s;' % id
    return _exec_sql(config, sql, db='nova')


def _get_image_in_db(config, id):
    sql = 'select id, status, deleted from images where id = %s;' % id
    return _exec_sql(config, sql, db='glance')


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
