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
    def __init__(self, cwd, command):
        self._process = None
        self.cwd = cwd
        self.command = command
        self.env = None

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
    def __init__(self, directory, config):
        super(GlanceRegistryProcess, self)\
                .__init__(directory,
                          "bin/glance-registry --config-file=%s" % config)


class GlanceApiProcess(Process):
    def __init__(self, directory, config, host, port):
        super(GlanceApiProcess, self)\
                .__init__(directory,
                          "bin/glance-api --config-file=%s" % config)
        self.host = host
        self.port = port

    def start(self):
        super(GlanceApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class KeystoneProcess(Process):
    def __init__(self, directory, config, host, port):
        super(KeystoneProcess, self)\
                .__init__(directory,
                          "bin/keystone --config-file %s -d" % config)
        self.host = host
        self.port = port

    def start(self):
        super(KeystoneProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaProcess(Process):
    lock_path = '/tmp/nova_locks'

    def __init__(self, cwd, command):
        command += ' --lock_path=%s' % self.lock_path
        super(NovaProcess, self)\
                .__init__(cwd, command)

    def start(self):
        subprocess.check_call('mkdir -p %s' % self.lock_path, shell=True)
        super(NovaProcess, self).start()

    def stop(self):
        super(NovaProcess, self).stop()
        subprocess.check_call('rm -rf %s' % self.lock_path, shell=True)


class NovaApiProcess(NovaProcess):
    def __init__(self, directory, host, port):
        super(NovaApiProcess, self)\
                .__init__(directory, "bin/nova-api")
        self.host = host
        self.port = port

    def start(self):
        super(NovaApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaComputeProcess, self)\
                .__init__(directory, "sg libvirtd bin/nova-compute")

    def start(self):
        super(NovaComputeProcess, self).start()
        time.sleep(5)

    def stop(self):
        kill_children_process(self._process.pid)
        super(NovaComputeProcess, self).stop()


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaNetworkProcess, self)\
                .__init__(directory, "bin/nova-network")


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaSchedulerProcess, self)\
                .__init__(directory, "bin/nova-scheduler")


class QuantumProcess(Process):
    def __init__(self, directory, config):
        super(QuantumProcess, self)\
                .__init__(directory, "bin/quantum " + config)


class QuantumPluginOvsAgentProcess(Process):
    def __init__(self, directory, config):
        super(QuantumPluginOvsAgentProcess, self)\
                .__init__(directory, "sudo python "
                                     "quantum/plugins/"
                                         "openvswitch/agent/"
                                         "ovs_quantum_agent.py "
                                     "-v " + config)

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None
