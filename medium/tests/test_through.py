import base64
import os
import re
import subprocess
import time
import urllib

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import exceptions
from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""


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

    def start(self):
        self._process = subprocess.Popen(self.command,
                                         cwd=self.cwd)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class GlanceRegistryProcess(Process):
    def __init__(self, directory, config):
        super(GlanceRegistryProcess, self)\
                .__init__(directory,
                          ["bin/glance-registry",
                           "--config-file=%s" % config])


class GlanceApiProcess(Process):
    def __init__(self, directory, config, host, port):
        super(GlanceApiProcess, self)\
                .__init__(directory,
                          ["bin/glance-api",
                           "--config-file=%s" % config])
        self.host = host
        self.port = port

    def start(self):
        super(GlanceApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class KeystoneProcess(Process):
    def __init__(self, directory, config, host, port):
        super(KeystoneProcess, self)\
                .__init__(directory,
                          ["bin/keystone",
                           "--config-file", config,
                           "-d"])
        self.host = host
        self.port = port

    def start(self):
        super(KeystoneProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaProcess(Process):
    lock_path = '/tmp/nova_locks'

    def __init__(self, cwd, command):
        command = list(command)
        command.append('--lock_path=%s' % self.lock_path)
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
                .__init__(directory, ["bin/nova-api"])
        self.host = host
        self.port = port

    def start(self):
        super(NovaApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaComputeProcess, self)\
                .__init__(directory, ["sg", "libvirtd",
                                      "bin/nova-compute"])

    def start(self):
        super(NovaComputeProcess, self).start()
        time.sleep(5)

    def stop(self):
        kill_children_process(self._process.pid)
        super(NovaComputeProcess, self).stop()


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaNetworkProcess, self)\
                .__init__(directory, ["bin/nova-network"])


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaSchedulerProcess, self)\
                .__init__(directory, ["bin/nova-scheduler"])


class QuantumProcess(Process):
    def __init__(self, directory, config):
        super(QuantumProcess, self)\
                .__init__(directory, ["bin/quantum", config])


class QuantumPluginOvsAgentProcess(Process):
    def __init__(self, directory, config):
        super(QuantumPluginOvsAgentProcess, self)\
                .__init__(directory, ["sudo", "python",
                                      "quantum/plugins/"
                                          "openvswitch/agent/"
                                          "ovs_quantum_agent.py",
                                      config,
                                      "-v"])

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None


default_config = storm.config.StormConfig('etc/medium.conf')
config = default_config
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # glance.
    environ_processes.append(GlanceRegistryProcess(
            config.glance.directory,
            config.glance.registry_config))
    environ_processes.append(GlanceApiProcess(
            config.glance.directory,
            config.glance.api_config,
            config.glance.host,
            config.glance.port))

    # keystone.
    environ_processes.append(KeystoneProcess(
            config.keystone.directory,
            config.keystone.config,
            config.keystone.host,
            config.keystone.port))

    # quantum.
    environ_processes.append(QuantumProcess(
        config.quantum.directory,
        config.quantum.config))
    environ_processes.append(QuantumPluginOvsAgentProcess(
        config.quantum.directory,
        config.quantum.agent_config))

    for process in environ_processes:
        process.start()
    time.sleep(10)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaComputeProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        # reset db.
        subprocess.check_call('mysql -uroot -ppassword -e "'
                              'DROP DATABASE IF EXISTS nova;'
                              'CREATE DATABASE nova;'
                              '"',
                              shell=True)
        subprocess.call(['bin/nova-manage', 'db', 'sync'],
                        cwd=self.config.nova.directory)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

    def tearDown(self):
        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            (id, name, state) = line.split()
            if state == 'running':
                subprocess.check_call('virsh destroy %s' % id, shell=True)
            subprocess.check_call('virsh undefine %s' % name, shell=True)

        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]


class ServersTest(FunctionalTest):
    def setUp(self):
        super(ServersTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

    @attr(type='smoke')
    def test_through(self):
        print """

        creating server.

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_existing(server['id'])

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_existing(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_existing(alt_img_id)


class FlavorsTest(FunctionalTest):
    # Almost same as storm.tests.test_flavors, but extends MT environment behavior.

    def setUp(self):
        super(FlavorsTest, self).setUp()
        self.flavor_ref = self.config.env.flavor_ref
        self.client = self.os.flavors_client

    @attr(type='smoke')
    def test_list_flavors(self):
        """ List of all flavors should contain the expected flavor """
        resp, body = self.client.list_flavors()
        flavors = body['flavors']

        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        flavor_min_detail = {'id': flavor['id'], 'links': flavor['links'],
                             'name': flavor['name']}
        self.assertTrue(flavor_min_detail in flavors)

    @attr(type='smoke')
    def test_list_flavors_with_detail(self):
        """ Detailed list of all flavors should contain the expected flavor """
        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertTrue(flavor in flavors)

    @attr(type='smoke')
    def test_get_flavor(self):
        """ The expected flavor details should be returned """
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertEqual(self.flavor_ref, flavor['id'])
