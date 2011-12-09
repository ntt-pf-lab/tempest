import os
import subprocess
import time
import urllib


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

    def __init__(self, cwd, command, **kwargs):
        command += ' --lock_path=%s' % self.lock_path
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

    def start(self):
        super(NovaApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaComputeProcess, self)\
                .__init__(directory, "sg libvirtd bin/nova-compute", **kwargs)

    def start(self):
        super(NovaComputeProcess, self).start()
        time.sleep(5)

    def stop(self):
        kill_children_process(self._process.pid)
        super(NovaComputeProcess, self).stop()


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaNetworkProcess, self)\
                .__init__(directory, "bin/nova-network", **kwargs)


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory, **kwargs):
        super(NovaSchedulerProcess, self)\
                .__init__(directory, "bin/nova-scheduler", **kwargs)


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
