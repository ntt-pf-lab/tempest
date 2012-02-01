import os
import subprocess
import time
import urllib
from stackmonkey import manager


def wait_to_launch(host, port):
    while True:
        try:
            urllib.urlopen('http://%(host)s:%(port)s/' % locals())
            time.sleep(.1)
            break
        except IOError:
            pass


def kill_children_process(pid, force=False):
    pid = int(pid)
    for line in subprocess.check_output(
            '/bin/ps -eo "ppid pid"',
            shell=True).split('\n')[1:]:
        line = line.strip()
        if line:
            ppid, child_pid = line.split()
            ppid = int(ppid)
            child_pid = int(child_pid)
            if ppid == pid:
                kill_children_process(child_pid, force=force)
                if force:
                    os.system('/usr/bin/sudo /bin/kill %d' % child_pid)
                else:
                    os.system('/bin/kill %d' % child_pid)


class Process(object):
    def __init__(self, cwd, command, env=None):
        self._process = None
        self.cwd = cwd
        self.command = command
        self.env = env

    def start(self):
        self._process = subprocess.Popen(self.command,
                                         cwd=self.cwd, shell=True,
                                         env=self.env)
        assert self._process.returncode is None

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None


class GlanceRegistryProcess(Process):
    def __init__(self, directory, config, **kwargs):
        self.registry_havoc = manager.GlanceHavoc(registry_config_file=config,
                **kwargs)

    def start(self):
        self.registry_havoc.start_glance_registry()

    def stop(self):
        self.registry_havoc.stop_glance_registry()


class GlanceApiProcess(Process):
    def __init__(self, directory, config, host, port, **kwargs):
        self.glance_api_havoc = manager.GlanceHavoc(host, api_config_file=config,
                **kwargs)

    def start(self):
        self.glance_api_havoc.start_glance_api()

    def stop(self):
        self.glance_api_havoc.stop_glance_api()


class KeystoneProcess(Process):
    def __init__(self, directory, config, host, port, **kwargs):
        self.keystone_havoc = manager.KeystoneHavoc(host, config_file=config,
                **kwargs)

    def start(self):
        self.keystone_havoc.start_keystone()

    def stop(self):
        self.keystone_havoc.stop_keystone()


class NovaProcess(Process):
    lock_path = '/tmp/nova_locks'
    monkey_patch = True

    def __init__(self, cwd, command, patches=[], **kwargs):
        command += ' --lock_path=%s' % self.lock_path
        if self.monkey_patch:
            # a patch entry be formed as (module, patch)
            command += ' --monkey_patch=true'
            command += ' --monkey_patch_modules=%s' % ','.join([
                module + ':' + patch
                for module, patch in patches
            ])
        super(NovaProcess, self)\
                .__init__(cwd, command, **kwargs)

    def start(self):
        subprocess.check_call('mkdir -p %s' % self.lock_path, shell=True)
        super(NovaProcess, self).start()

    def stop(self):
        super(NovaProcess, self).stop()
        subprocess.check_call('rm -rf %s' % self.lock_path, shell=True)


class NovaApiProcess(NovaProcess):
    def __init__(self, directory, host, port, **kwargs):
        self.api_havoc = manager.ControllerHavoc(host, **kwargs)

    def start(self):
        self.api_havoc.start_nova_api()

    def stop(self):
        self.api_havoc.stop_nova_api()


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        self.compute_havoc = manager.ComputeHavoc(**kwargs)

    def start(self):
        self.compute_havoc.start_nova_compute()

    def stop(self):
        self.compute_havoc.stop_nova_compute()


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        self.network_havoc = manager.NetworkHavoc(**kwargs)

    def start(self):
        self.network_havoc.start_nova_network()

    def stop(self):
        self.network_havoc.stop_nova_network()


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        self.scheduler_havoc = manager.ControllerHavoc(**kwargs)

    def start(self):
        self.scheduler_havoc.start_nova_scheduler()

    def stop(self):
        self.scheduler_havoc.stop_nova_scheduler()


class QuantumProcess(Process):
    def __init__(self, directory, config, **kwargs):
        self.quantum_havoc = manager.QuantumHavoc(config_file=config, **kwargs)

    def start(self):
        self.quantum_havoc.start_quantum()

    def stop(self):
        self.quantum_havoc.stop_quantum()


class QuantumPluginOvsAgentProcess(Process):
    def __init__(self, directory, config, **kwargs):
        self.havoc = manager.QuantumHavoc(agent_config_file=config, **kwargs)

    def start(self):
        self.havoc.start_quantum_plugin()

    def stop(self):
        self.havoc.stop_quantum_plugin()


# Fakes
class FakeQuantumProcess(Process):
    def __init__(self, tenant_id, **status_code):
        cwd = os.path.join(os.path.dirname(__file__),
                           'quantum-service-fake')
        command = os.path.join(cwd, 'fake_server.py')
        command += ' --debug'
        command += ' --tenant=%s' % tenant_id
        command += ' --tenant=default'
        for pair in status_code.items():
            command += ' --%s=%d' % pair
        super(FakeQuantumProcess, self)\
                .__init__(cwd, command)

    def start(self):
        super(FakeQuantumProcess, self).start()
        time.sleep(1)

    def set_test(self, flag):
        import json
        import httplib

        headers = {'Content-Type': 'application/json'}
        body = json.dumps({'test': flag})
        conn = httplib.HTTPConnection('127.0.0.1', 9696)
        conn.request('POST', '/_backdoor', body, headers)
        conn.close()
