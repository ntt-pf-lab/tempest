import os
import signal
import subprocess
import time
import urllib
from nose.plugins.attrib import attr
from storm import openstack
from storm.common.utils.data_utils import rand_name
import base64
import medium.config
import unittest2 as unittest


def wait_to_be_launched(host, port):
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


class GlanceRegistryProcess(object):
    def __init__(self, directory, config):
        self.directory = directory
        self.config = config
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/glance-registry",
                                          "--config-file=%s" % self.config],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class GlanceApiProcess(object):
    def __init__(self, directory, config, host, port):
        self.directory = directory
        self.config = config
        self.host = host
        self.port = port
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/glance-api",
                                          "--config-file=%s" % self.config],
                                         cwd=self.directory)
        assert self._process.returncode is None
        wait_to_be_launched(self.host, self.port)

    def stop(self):
        self._process.terminate()
        self._process = None


class KeystoneProcess(object):
    def __init__(self, directory, config, host, port):
        self.directory = directory
        self.config = config
        self.host = host
        self.port = port
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/keystone",
                                          "--config-file", self.config,
                                          "-d"],
                                         cwd=self.directory)
        assert self._process.returncode is None
        wait_to_be_launched(self.host, self.port)

    def stop(self):
        self._process.terminate()
        self._process = None


class NovaApiProcess(object):
    def __init__(self, directory, host, port):
        self.directory = directory
        self.host = host
        self.port = port
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/nova-api"],
                                         cwd=self.directory)
        assert self._process.returncode is None
        wait_to_be_launched(self.host, self.port)

    def stop(self):
        self._process.terminate()
        self._process = None


class NovaComputeProcess(object):
    def __init__(self, directory):
        self.directory = directory
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["sg", "libvirtd",
                                          "bin/nova-compute"],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        kill_children_process(self._process.pid)
        self._process.terminate()
        self._process = None


class NovaNetworkProcess(object):
    def __init__(self, directory):
        self.directory = directory
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/nova-network"],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class NovaSchedulerProcess(object):
    def __init__(self, directory):
        self.directory = directory
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/nova-scheduler"],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class QuantumProcess(object):
    def __init__(self, directory, config):
        self.directory = directory
        self.config = config
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/quantum",
                                          self.config],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class QuantumPluginOvsAgentProcess(object):
    def __init__(self, directory, config):
        self.directory = directory
        self.config = config
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["sudo", "python",
                                          "quantum/plugins/"
                                              "openvswitch/agent/"
                                              "ovs_quantum_agent.py",
                                          self.config,
                                          "-v"],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None


class ServersTest(unittest.TestCase):

    config_path = 'etc/medium.config.ini'

    @classmethod
    def setUpClass(cls):
        cls.environment_processes = processes = []
        cls.config = medium.config.MediumConfig(cls.config_path)

        # glance.
        processes.append(GlanceRegistryProcess(
                cls.config.glance.directory,
                cls.config.glance.registry_config))
        processes.append(GlanceApiProcess(
                cls.config.glance.directory,
                cls.config.glance.api_config,
                cls.config.glance.host,
                cls.config.glance.port))

        # keystone.
        processes.append(KeystoneProcess(
                cls.config.keystone.directory,
                cls.config.keystone.config,
                cls.config.keystone.host,
                cls.config.keystone.port))

        # quantum
        processes.append(QuantumProcess(
            cls.config.quantum.directory,
            cls.config.quantum.config))
        time.sleep(10)
        processes.append(QuantumPluginOvsAgentProcess(
            cls.config.quantum.directory,
            cls.config.quantum.agent_config))

        for process in processes:
            process.start()
        # cls.os = openstack.Manager()
        # cls.client = cls.os.servers_client
        # cls.image_ref = cls.config.env.image_ref
        # cls.flavor_ref = cls.config.env.flavor_ref
        # cls.ssh_timeout = cls.config.nova.ssh_timeout

    @classmethod
    def tearDownClass(cls):
        for process in cls.environment_processes:
            process.stop()

    def setUp(self):
        self.testing_processes = processes = []

        # nova.
        processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        processes.append(NovaComputeProcess(
                self.config.nova.directory))
        processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        for process in processes:
            process.start()

    def tearDown(self):
        for process in self.testing_processes:
            process.stop()

    @attr(type='smoke')
    def test_through(self):
        pass
        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 meta=meta,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6,
                                                 personality=personality)

        #Wait for the server to become active
        self.client.wait_for_server_status(server['id'], 'ACTIVE')

        #Verify the specified attributes are set correctly
        resp, server = self.client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(self.image_ref, server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        #Teardown
        self.client.delete_server(self.id)
        """
