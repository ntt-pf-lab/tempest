import os
import re
import subprocess
import tempfile
import time
import utils

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
import storm.config
from storm import exceptions
from storm.common.utils.data_utils import rand_name
from storm.services.keystone.json.keystone_client import TokenClient
import stackmonkey.manager as ssh_manager
from nova import test

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        FakeQuantumProcess)
from medium.tests.utils import (
        emphasised_print, silent_check_call,
        cleanup_virtual_instances, cleanup_processes)

config = storm.config.StormConfig('etc/large.conf')
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # glance
    environ_processes.append(GlanceRegistryProcess(
            config.glance.directory,
            config.glance.registry_config))
    environ_processes.append(GlanceApiProcess(
            config.glance.directory,
            config.glance.api_config,
            config.glance.host,
            config.glance.port))

    # keystone
    environ_processes.append(KeystoneProcess(
            config.keystone.directory,
            config.keystone.config,
            config.keystone.host,
            config.keystone.port))

    # quantum
    environ_processes.append(FakeQuantumProcess('1'))
#    environ_processes.append(QuantumProcess(
#        config.quantum.directory,
#        config.quantum.config))
#    environ_processes.append(QuantumPluginOvsAgentProcess(
#        config.quantum.directory,
#        config.quantum.agent_config))

    for process in environ_processes:
        process.start()
    time.sleep(10)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class FunctionalTest(unittest.TestCase):

    def setUp(self):
        emphasised_print(self.id())

        self.havoc = ssh_manager.HavocManager()
        self.ssh_con = self.havoc.connect('127.0.0.1', 'openstack',
                        'openstack', self.havoc.config.nodes.ssh_timeout)
        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
        self.testing_processes = []

    def tearDown(self):
        pass

    def reset_db(self):
        silent_check_call('mysql -u%s -p%s -h%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password,
                              self.config.mysql.host),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.nova.directory, shell=True)


class FaultRecoveryTest(FunctionalTest):

    config = config

    def setUp(self):
        super(FaultRecoveryTest, self).setUp()

        # nova
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaComputeProcess(
                self.config.nova.directory,
                config_file=self.config.nova.config))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

#        # glance
#        self.testing_processes.append(GlanceRegistryProcess(
#                self.config.glance.directory,
#                self.config.glance.registry_config))
#        self.testing_processes.append(GlanceApiProcess(
#                self.config.glance.directory,
#                self.config.glance.api_config,
#                self.config.glance.host,
#                self.config.glance.port))
#
#        # keystone
#        self.testing_processes.append(KeystoneProcess(
#                config.keystone.directory,
#                config.keystone.config,
#                config.keystone.host,
#                config.keystone.port))
#
#        # quantum
#        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db
        self.reset_db()

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def tearDown(self):
        super(FaultRecoveryTest, self).tearDown()

    def _create_3_servers(self):
        # create 3 servers
        accessIPv4_1 = '1.1.1.1'
        accessIPv6_1 = '2002:0101:0101::/48'
        server_name_1 = rand_name(self._testMethodName) + '_1'
        _, server = self.ss_client.create_server(server_name_1,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4_1,
                                                 accessIPv6=accessIPv6_1)
        server_id_1 = server['id']
        self.ss_client.wait_for_server_status(server_id_1, 'ACTIVE')

        accessIPv4_2 = '1.1.1.2'
        accessIPv6_2 = '2002:0101:0102::/48'
        server_name_2 = rand_name(self._testMethodName) + '_2'
        _, server = self.ss_client.create_server(server_name_2,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4_2,
                                                 accessIPv6=accessIPv6_2)
        server_id_2 = server['id']
        self.ss_client.wait_for_server_status(server_id_2, 'ACTIVE')

        accessIPv4_3 = '1.1.1.3'
        accessIPv6_3 = '2002:0101:0103::/48'
        server_name_3 = rand_name(self._testMethodName) + '_3'
        _, server = self.ss_client.create_server(server_name_3,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4_3,
                                                 accessIPv6=accessIPv6_3)
        server_id_3 = server['id']

        return server_id_1, server_id_2, server_id_3

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_1(self):
        """
        Stop nova-compute process during creating server,
        then restart nova-compute
        """
        # create 3 servers
        server_id_1, server_id_2, server_id_3 = self._create_3_servers()

        # stop nova-compute process during creating 3rd server
        for process in self.testing_processes[:]:
            if isinstance(process, NovaComputeProcess):
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

        # restart process
        process.start()
        self.testing_processes.append(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_2(self):
        """
        Stop nova-network process during creating server,
        then restart nova-network
        """
        # create 3 servers
        server_id_1, server_id_2, server_id_3 = self._create_3_servers()

        # stop nova-network process during creating 3rd server
        for process in self.testing_processes[:]:
            if isinstance(process, NovaApiProcess):
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is NG

        # restart process
        process.start()
        self.testing_processes.append(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_3(self):
        """
        Stop Melange process during creating server,
        then restart Melange
        """
        # create 3 servers
        server_id_1, server_id_2, server_id_3 = self._create_3_servers()

        # stop Melange process during creating 3rd server
        # TODO stop Melange process

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is NG

        # restart process
        # TODO start Melange process

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_4(self):
        """
        Stop NVP process during creating server,
        then restart NVP
        """
        # create 3 servers
        server_id_1, server_id_2, server_id_3 = self._create_3_servers()

        # stop NVP process during creating 3rd server
        # TODO stop NVP process

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

        # restart process
        # TODO start NVP process

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_5(self):
        """
        Stop nova-scheduler process during creating server,
        then restart nova-scheduler
        """
        # create 3 servers
        server_id_1, server_id_2, server_id_3 = self._create_3_servers()

        # stop nova-scheduler process during creating 3rd server
        for process in self.testing_processes[:]:
            if isinstance(process, NovaSchedulerProcess):
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK

        # restart process
        process.start()
        self.testing_processes.append(process)
        time.sleep(10)

        # list servers
        resp, body = self.ss_client.list_servers()
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))
        for server in body['servers']:
            self.assertIn(server['id'], [server_id_1, server_id_2])

        # ping to server
        # TODO assert that ping/ssh is OK
