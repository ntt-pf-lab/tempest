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
        self.deploy_mode == 'devstack-local'

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
        super(GlanceRegistryProcess, self)\
                .__init__(directory,
                          "bin/glance-registry --config-file=%s" % config,
                          **kwargs)


class GlanceApiProcess(Process):
    def __init__(self, directory, config, host, port, **kwargs):
        super(GlanceApiProcess, self)\
                .__init__(directory,
                          "bin/glance-api --config-file=%s" % config,
                          **kwargs)
        self.host = host
        self.port = port

    def start(self):
        super(GlanceApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class KeystoneProcess(Process):
    def __init__(self, directory, config, host, port, **kwargs):
        super(KeystoneProcess, self)\
                .__init__(directory,
                          "bin/keystone --config-file %s -d" % config,
                          **kwargs)
        self.host = host
        self.port = port

    def start(self):
        super(KeystoneProcess, self).start()
        wait_to_launch(self.host, self.port)


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
        super(NovaApiProcess, self)\
                .__init__(directory, "bin/nova-api", **kwargs)
        self.host = host
        self.port = port
        self.havoc = manager.ControllerHavoc(host, **kwargs)

    def start(self):
        self.havoc.start_nova_api()
        #wait_to_launch(self.host, self.port)

    def stop(self):
        self.havoc.stop_nova_api()


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaComputeProcess, self)\
                .__init__(directory, "bin/nova-compute", **kwargs)
        self.havoc = manager.ComputeHavoc(**kwargs)

    def start(self):
        if getattr(self, '_wrapped_command', None) is None:
            self._original_command = self.command
            self._wrapped_command = "sg libvirtd '%s'" % self.command
        self.command = self._wrapped_command
        self.havoc.start_nova_compute()
        #super(NovaComputeProcess, self).start()
        time.sleep(5)

    def stop(self):
        self.havoc.stop_nova_compute()
        #kill_children_process(self._process.pid)


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaNetworkProcess, self)\
                .__init__(directory, "bin/nova-network", **kwargs)
        self.havoc = manager.NetworkHavoc(**kwargs)

    def start(self):
        self.havoc.start_nova_network()

    def stop(self):
        self.havoc.stop_nova_network()


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaSchedulerProcess, self)\
                .__init__(directory, "bin/nova-scheduler", **kwargs)
        self.havoc = manager.ControllerHavoc(**kwargs)

    def start(self):
        self.havoc.start_nova_scheduler()

    def stop(self):
        self.havoc.stop_nova_scheduler()


class QuantumProcess(Process):
    def __init__(self, directory, config, **kwargs):
        super(QuantumProcess, self)\
                .__init__(directory, "bin/quantum " + config, **kwargs)


class QuantumPluginOvsAgentProcess(Process):
    def __init__(self, directory, config, **kwargs):
        super(QuantumPluginOvsAgentProcess, self)\
                .__init__(directory, "sudo python "
                                     "quantum/plugins/"
                                         "openvswitch/agent/"
                                         "ovs_quantum_agent.py "
                                     "-v " + config,
                          **kwargs)

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None


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
