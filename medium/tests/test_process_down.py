# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 NTT
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import base64
import re
import subprocess
import time
import json

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
from storm import openstack
from storm.common.utils.data_utils import rand_name
from storm import exceptions
from nova import utils
from nova import test

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess)

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

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
    time.sleep(10)
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
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'DROP DATABASE IF EXISTS nova;'
                              'CREATE DATABASE nova;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
        subprocess.call('/opt/openstack/nova/bin/nova-manage db sync',
                        cwd=self.config.nova.directory, shell=True)

        time.sleep(0)
        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage user create '
                              '--name=admin --access=secrete --secret=secrete',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage user create '
                              '--name=demo --access=secrete --secret=secrete',
                              cwd=self.config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage project create '
                              '--project=1 --user=admin',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage project create '
                              '--project=2 --user=demo',
                              cwd=self.config.nova.directory, shell=True)

        # allocate networks.
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage network create '
                              '--label=private_1-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.0.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage network create '
                              '--label=private_1-2 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.1.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage network create '
                              '--label=private_2-1 '
                              '--project_id=2 '
                              '--fixed_range_v4=10.0.2.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)

    def tearDown(self):
        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            (id, name, state) = line.split()
            if state == 'running':
                subprocess.check_call('virsh destroy %s' % id, shell=True)
            subprocess.check_call('virsh undefine %s' % name, shell=True)

        for process in self.testing_processes:
            if process:
                process.stop()
        del self.testing_processes[:]
        time.sleep(10)
        self._dumpdb()

        subprocess.call('sudo service rabbitmq-server restart',
                        cwd=self.config.nova.directory, shell=True)

    def exec_sql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -e "' + sql + '"'
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                              shell=True)

    def get_data_from_mysql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.user,
                                         self.config.mysql.password),
                                         shell=True)
        return result

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)


class ProcessDownTestCase(FunctionalTest):
    def setUp(self):
        super(ProcessDownTestCase, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
#        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_nova_compute_down_for_create(self):
        """test for nova-compute process is down"""
        print """

        test_nova_compute_down_for_create

        """
        for process in self.testing_processes:
            if process.command.find('nova-compute') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

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

        self.assertEqual(True, int(resp['status']) >= 500)

    @attr(kind='medium')
    def test_nova_network_down_for_create(self):
        """test for nova-network process is down"""
        print """

        test_nova_network_down_for_create

        """
        for process in self.testing_processes:
            if process.command.find('nova-network') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

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

        time.sleep(10)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'BUILD')
        resp, body = self.ss_client.list_servers({'status': 'ERROR'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_nova_scheduler_down_for_create(self):
        """test for nova-scheduler process is down"""
        print """

        test_nova_scheduler_down_for_create

        """
        for process in self.testing_processes:
            if process.command.find('nova-scheduler') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

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
        time.sleep(10)

        self.assertEqual('500', resp['status'])

    @attr(kind='medium')
    def test_nova_api_down_for_create(self):
        """test for nova-api process is down"""
        print """

        test_nova_api_down_for_create

        """
        for process in self.testing_processes:
            if process.command.find('nova-api') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

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
        self.assertEqual('408', resp['status'])

    @attr(kind='medium')
    def test_nova_compute_down_for_reboot(self):
        """test for nova-compute process is down"""
        print """

        test_nova_compute_down_reboot

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-compute') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.reboot(sid, 'HARD')

        self.assertEqual(True, int(resp['status']) >= 500)

    @attr(kind='medium')
    def test_nova_network_down_for_reboot(self):
        """test for nova-network process is down"""
        print """

        test_nova_network_down_for_reboot

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-network') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.reboot(sid, 'HARD')

        time.sleep(10)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(sid, 'REBOOT')
        resp, body = self.ss_client.list_servers({'status': 'ERROR'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_nova_scheduler_down_for_reboot(self):
        """test for nova-scheduler process is down"""
        print """

        test_nova_scheduler_down_for_reboot

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-scheduler') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.reboot(sid, 'HARD')

        self.assertEqual(True, int(resp['status']) >= 500)

    @attr(kind='medium')
    def test_nova_api_down_for_reboot(self):
        """test for nova-api process is down"""
        print """

        test_nova_api_down_for_reboot

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-api') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.reboot(sid, 'HARD')

        self.assertEqual('408', resp['status'])

    @attr(kind='medium')
    def test_nova_compute_down_for_delete(self):
        """test for nova-compute process is down"""
        print """

        test_nova_compute_down_for_delete

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-compute') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.delete_server(sid)

        self.assertEqual(True, int(resp['status']) >= 500)

    @attr(kind='medium')
    def test_nova_network_down_for_delete(self):
        """test for nova-network process is down"""
        print """

        test_nova_network_down_for_delete

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-network') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.delete_server(sid)

        time.sleep(10)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(sid, 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ERROR'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_nova_scheduler_down_for_delete(self):
        """test for nova-scheduler process is down"""
        print """

        test_nova_scheduler_down_for_delete

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-scheduler') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.delete_server(sid)

        self.assertEqual(True, int(resp['status']) >= 500)

    @attr(kind='medium')
    def test_nova_api_down_for_delete(self):
        """test for nova-api process is down"""
        print """

        test_nova_api_down_for_delete

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        for process in self.testing_processes:
            if process.command.find('nova-api') >= 0:
                process.stop()
                self.testing_processes.remove(process)
        time.sleep(10)

        sid = server['id']
        resp, server = self.ss_client.delete_server(sid)

        self.assertEqual('408', resp['status'])

    @test.skip_test('waiting is too long')
    @attr(kind='medium')
    def test_rabbitmq_down_for_create(self):
        """test for rabbitmq process is down"""
        print """

        test_rabbitmq_down_for_create

        """
        subprocess.call('sudo service rabbitmq-server stop',
                        cwd=self.config.nova.directory, shell=True)

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

        self.assertEqual(True, int(resp['status']) >= 500)

    @test.skip_test('waiting is too long')
    @attr(kind='medium')
    def test_rabbitmq_down_for_reboot(self):
        """test for rabbitmq process is down"""
        print """

        test_rabbitmq_down_for_reboot

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        subprocess.call('sudo service rabbitmq-server stop',
                        cwd=self.config.nova.directory, shell=True)

        sid = server['id']
        resp, server = self.ss_client.reboot(sid, 'HARD')

        self.assertEqual(True, int(resp['status']) >= 500)

    @test.skip_test('waiting is too long')
    @attr(kind='medium')
    def test_rabbitmq_down_for_delete(self):
        """test for rabbitmq process is down"""
        print """

        test_rabbitmq_down_for_delete

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
                                                    personality=personality,
                                                    retry=True)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})

        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        subprocess.call('sudo service rabbitmq-server stop',
                        cwd=self.config.nova.directory, shell=True)

        sid = server['id']
        resp, server = self.ss_client.delete_server(sid)

        self.assertEqual(True, int(resp['status']) >= 500)
