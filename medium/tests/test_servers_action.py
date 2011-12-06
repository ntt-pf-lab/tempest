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

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name

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
        subprocess.call('bin/nova-manage db sync',
                        cwd=self.config.nova.directory, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        subprocess.check_call('bin/nova-manage user create '
                              '--name=admin --access=secrete --secret=secrete',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage user create '
                              '--name=demo --access=secrete --secret=secrete',
                              cwd=self.config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('bin/nova-manage project create '
                              '--project=1 --user=admin',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage project create '
                              '--project=2 --user=demo',
                              cwd=self.config.nova.directory, shell=True)

        # allocate networks.
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_1-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.0.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_1-2 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.1.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage network create '
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
            process.stop()
        del self.testing_processes[:]


class ServersTest(FunctionalTest):
    def setUp(self):
        super(ServersTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client


    @attr(kind='medium')
    def test_reboot_when_specify_not_exist_server_id(self):
        print """

        reboot server

         """
        test_id = 5
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        print "A00_62 resp= ", resp
        print "A00_62 server= ", server
        self.assertEqual('404', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(test_id)
        self.ss_client.wait_for_server_not_exists(test_id)

    @attr(kind='medium')
    def test_reboot_when_server_is_during_boot_process(self):
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

        resp, server = self.ss_client.get_server(server['id'])
        test_id = server['id']
        self.assertEquals('BUILD', server['status'])

        print """

        reboot server without waiting done creating

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('202', resp['status'])
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_running(self):
        print """

        creating server.

        """
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = rand_name('instance')
        file_contents = 'This is a test_file.'
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
        test_id = server['id']
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'HARD')
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_during_reboot_process(self):
        print """

        creating server.

        """
        meta = {'open': 'stack'}
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
        test_id = server['id']
        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'HARD')
        self.assertEquals('202', resp['status'])
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])
        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'HARD')
        self.assertEquals('202', resp['status'])
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('ACTIVE', server['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_reboot_when_server_is_during_stop_process(self):
        print """

        creating server.

        """
        meta = {'open': 'stack'}
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
        test_id = server['id']
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Stop server
        resp, server = self.ss_client.delete_server(test_id)
        self.ss_client.wait_for_server_not_exists(test_id)
        self.assertEquals('204', resp['status'])

        # Reboot stopped server
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('422', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_reboot_when_server_is_down(self):
        print """

        creating server.

        """
        meta = {'open': 'stack'}
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
        test_id = server['id']
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')
        resp, server = self.ss_client.list_servers_with_detail()
        self.assertEquals('ACTIVE', server['servers'][0]['status'])

        # Stop server
        resp, server = self.ss_client.delete_server(test_id)
        time.sleep(10)
        resp, server = self.ss_client.list_servers_with_detail()
        self.assertEquals([], server['servers'])

        self.ss_client.wait_for_server_not_exists(test_id)
        self.assertEquals('200', resp['status'])

        # Wait for the server to become deleted
        self.ss_client.wait_for_server_not_exists(test_id)

        # Reboot stopped server
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('422', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_reboot_when_specify_hard_reboot_type(self):
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

        test_id = server['id']
        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'HARD')
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_reboot_when_specify_soft_reboot_type(self):
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

        test_id = server['id']
        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'SOFT')
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_reboot_specify_invalid_reboot_type(self):
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

        test_id = server['id']
        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'],
                                             'test_openstack_aaabbbccc')
        print "resp= ", resp
        print "server= ", server
        resp, server = self.ss_client.get_server(test_id)
        print "resp= ", resp
        print "server= ", server
        self.assertEquals('ACTIVE', server['status'])


        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        print "resp= ", resp
        print "server= ", server
        self.assertEqual('200', resp['status'])

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_create_image(self):
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
        resp, body = self.ss_client.list_servers_with_detail()

        print """

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

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
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)

    @attr(kind='medium')
    def test_create_image_specify_not_exist_server_id(self):
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
        resp, _ = self.ss_client.create_image(99, 'opst_test')

        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image('opst_test')
        self.img_client.wait_for_image_not_exists('opst_test')

    @attr(kind='medium')
    def test_create_image_when_server_is_during_boot_process(self):
        print """

        creating server.

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.2.3.4'
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

        resp, server = self.ss_client.get_server(server['id'])
        test_id = server['id']
        self.assertEquals('BUILD', server['status'])

        print """

        creating snapshot.

        """
        # Make snapshot without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, body = self.ss_client.list_servers_with_detail()

    @attr(kind='medium')
    def test_create_image_when_server_is_during_reboot_process(self):
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

        resp, server = self.ss_client.get_server(server['id'])
        test_id = server['id']
        self.assertEquals('BUILD', server['status'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(server['id'], 'HARD')
        self.assertEquals('202', resp['status'])
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        print """

        creating snapshot without waiting done rebooting server.

        """
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        print "resp=", resp
        resp1, images1 = self.img_client.list_images()
        print "resp1=", resp1
        print "images1=", images1
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, body = self.ss_client.list_servers_with_detail()


    @attr(kind='medium')
    def test_create_image_when_server_is_during_stop_process(self):
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

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
#        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        print "resp=", resp
        resp1, images1 = self.img_client.list_images()
        print "resp1=", resp1
        print "images1=", images1
        self.assertEquals('400', resp['status'])

        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_name)
        self.img_client.wait_for_image_not_exists(alt_name)

    @attr(kind='medium')
    def test_create_image_when_server_is_down(self):
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

        deleting server.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        print "resp=", resp
        self.assertEquals('400', resp['status'])

        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_name)
        self.img_client.wait_for_image_not_exists(alt_name)

    @attr(kind='medium')
    def test_create_image_when_specify_duplicate_image_name(self):
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

        creating snapshot again.

        """
        # Make snapshot of the instance.
        resp, _ = self.ss_client.create_image(server['id'], alt_name)

        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)

    @attr(kind='medium')
    def test_create_image_when_specify_length_over_256_name(self):
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
        alt_name = rand_name('a'*260)
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        print """

        deleting server again.

        """
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)