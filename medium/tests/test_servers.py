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
import sys

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

    def exec_sql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -e "' + sql +'"' 
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                              shell=True)

    def get_data_from_mysql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -Ns -e "' + sql +'"' 
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.user,
                                         self.config.mysql.password),
                                         shell=True)

        return result


class ServersTest(FunctionalTest):
    def setUp(self):
        super(ServersTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_list_servers_when_no_server_created(self):
        """If no server is created, return empty list"""
        print """

        test_list_servers_when_no_server_created

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_when_one_server_created(self):
        """if created one server, return list include one server"""
        print """

        test_list_servers_when_one_server_created

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

        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_when_three_servers_created(self):
        """if created three servers, return list include three servers"""
        print """

        test_list_servers_when_three_servers_created

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name,
                                                self.image_ref,
                                                self.flavor_ref,
                                                meta=meta,
                                                accessIPv4=accessIPv4,
                                                accessIPv6=accessIPv6,
                                                personality=personality)

            # Wait for the server to become active
            self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_status_is_deleted(self):
        """If server is deleted, return an empty list"""
        print """

        test_list_servers_status_is_deleted

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

        # Delete the server
        self.ss_client.delete_server(server['id'])

        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_detail_when_no_server_created(self):
        """If no server is created, return an empty list"""
        print """

        test_list_servers_detail_when_no_server_created

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_detail_when_one_server_created(self):
        """if created one server, return list include one server"""
        print """

        test_list_servers_detail_when_one_server_created

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

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))
        self.assertEqual(accessIPv4, body['servers'][0]['accessIPv4'])

    @attr(kind='medium')
    def test_list_servers_detail_when_three_servers_created(self):
        """if created three servers, return list include three servers"""
        print """

        test_list_servers_detail_when_three_servers_created

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name,
                                                self.image_ref,
                                                self.flavor_ref,
                                                meta=meta,
                                                accessIPv4=accessIPv4,
                                                accessIPv6=accessIPv6,
                                                personality=personality)

            # Wait for the server to become active
            self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(body['servers']))
        for i in range(0, 3):
            self.assertEqual(accessIPv4, body['servers'][i]['accessIPv4'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_building(self):
        """if status is building, return status:BUILD"""
        print """

        test_list_servers_detail_status_is_building

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

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('BUILD', body['servers'][0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_active(self):
        """if status is active, return status:ACTIVE"""
        print """

        test_list_servers_detail_status_is_active

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

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('ACTIVE', body['servers'][0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_after_delete_server(self):
        """Immediately after delete server, status is active"""
        print """

        test_list_servers_detail_after_delete_server

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

        # Delete the server
        self.ss_client.delete_server(server['id'])

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('ACTIVE', body['servers'][0]['status'])

        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_deleted(self):
        """If server is deleted, return an empty list"""
        print """

        test_list_servers_detail_after_delete_server

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

        # Delete the server
        self.ss_client.delete_server(server['id'])

        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_image(self):
        print """

        test_list_servers_specify_exists_image

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

        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        #creating server from snapshot.
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.list_servers({'image': self.image_ref})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

        resp, body = self.ss_client.list_servers({'image': alt_img_id})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_image(self):
        print """

        test_list_servers_specify_not_exists_image

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

        resp, body = self.ss_client.list_servers({'image': 99})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_string_to_image(self):
        print """

        test_list_servers_specify_string_to_image

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

        resp, body = self.ss_client.list_servers({'image': 'image'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_image(self):
        print """

        test_list_servers_specify_overlimits_to_image

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

        resp, body = self.ss_client.list_servers({'image': sys.maxint + 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_image(self):
        print """

        test_list_servers_specify_negative_to_image

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

        resp, body = self.ss_client.list_servers({'image': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_flavor(self):
        print """

        test_list_servers_specify_exists_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': self.flavor_ref})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_flavor(self):
        print """

        test_list_servers_specify_not_exists_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': 99})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
#        msg = "The resource could not be found."
#        self.assertEqual('404', resp['status'])
#        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_list_servers_specify_string_to_flavor(self):
        print """

        test_list_servers_specify_string_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': 'flavor'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_flavor(self):
        print """

        test_list_servers_specify_overlimits_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': sys.maxint + 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_flavor(self):
        print """

        test_list_servers_specify_negative_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_server_name(self):
        print """

        test_list_servers_specify_exists_server_name

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

        resp, body = self.ss_client.list_servers({'name': name})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))
        self.assertEqual(name, body['servers'][0]['name'])

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_server_name(self):
        print """

        test_list_servers_specify_not_exists_server_name

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

        resp, body = self.ss_client.list_servers({'name': 'servername'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_empty_to_server_name(self):
        print """

        test_list_servers_specify_empty_to_server_name

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

        resp, body = self.ss_client.list_servers({'name': ''})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_server_name(self):
        print """

        test_list_servers_specify_overlimits_to_server_name

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

        resp, body = self.ss_client.list_servers({'name': 'a'*256})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_create_servers_not_active_image(self):
        """Ensure return error code 400 when specify not active image"""
        print """

        test_create_servers_not_active_image

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

        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

        resp, body = self.ss_client.create_server(name,
                                                  alt_img_id,
                                                  self.flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)
        print "resp=", resp
        print "body=", body
        msg = ("Cannot find requested image %(alt_img_id)s: "
               "Image %(alt_img_id)s is unacceptable: "
               "status is not active") % locals()
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_server_any_name(self):
        """Ensure create with the specified name"""
        print """

        test_create_server_any_name

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

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])
        self.assertEqual(name, server['name'])

    @attr(kind='medium')
    def test_create_server_name_is_num(self):
        """Ensure return error response Code 400 when name's type is numeric"""
        print """

        test_create_server_name_is_num

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 12345
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server(name,
                                                  self.image_ref,
                                                  self.flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Server name is not a string or unicode"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_server_name_is_empty(self):
        """Ensure return error response Code 400 when name is empty"""
        print """

        test_create_server_name_is_empty

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = ''
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server(name,
                                                  self.image_ref,
                                                  self.flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Server name is an empty string"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_server_names_length_over_256(self):
        """Ensure return error response Code 400 when name is over length"""
        print """

        test_create_server_names_length_over_256

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'a'*256
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

        print "resp=", resp
        print "server=", server
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_server_with_the_same_name(self):
        """Ensure create server when there is a server with the same name"""
        print """

        test_create_server_with_the_same_name

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
        id1 = server['id']

        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        id2 = server['id']

        resp, server = self.ss_client.get_server(id1)
        name1 = server['name']
        resp, server = self.ss_client.get_server(id2)
        name2 = server['name']
        self.assertEqual(name1, name2)

    @attr(kind='medium')
    def test_create_server_specify_exists_image(self):
        """Ensure create server when specify exists image"""
        print """

        test_create_server_specify_exists_image

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
        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])
        self.assertEqual(str(self.image_ref), server['image']['id'])

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_image(self):
        """Ensure return error code 400 when specify not exists image"""
        print """

        test_create_servers_specify_not_exists_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        image_ref = 99
        resp, body = self.ss_client.create_server(name,
                                                  image_ref,
                                                  self.flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        msg = ("Cannot find requested image %(image_ref)s: "
               "Image %(image_ref)s could not be found.") % locals()
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_not_specify_image(self):
        """Ensure return error code 400 when not specify image"""
        print """

        test_list_servers_not_specify_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     flavorRef=self.flavor_ref,
                                                     meta=meta,
                                                     accessIPv4=accessIPv4,
                                                     accessIPv6=accessIPv6,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Missing imageRef attribute"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_specify_invalid_fixed_ip_address(self):
        print """

        test_create_servers_specify_invalid_fixed_ip_address
        """

        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '1.2.3.4.5.6.7.8.9',
                     'uuid':uuid}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     networks=networks,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Invalid fixed IP address (1.2.3.4.5.6.7.8.9)"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_specify_invalid_uuid(self):
        print """

        test_create_servers_specify_invalid_uuid

        """

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.1.1',
                     'uuid':'a-b-c-d-e-f-g-h-i-j'}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     networks=networks,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        msg = ("Bad networks format: network uuid is not in "
               "proper format (a-b-c-d-e-f-g-h-i-j)")
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_server_specify_exists_flavor(self):
        """Ensure create server when specify exists flavor"""
        print """

        test_create_server_specify_exists_flavor

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
        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_flavor(self):
        """Ensure return error code 400 when specify not exists flavor"""
        print """

        test_create_servers_specify_not_exists_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        flavor_ref = 99
        resp, body = self.ss_client.create_server(name,
                                                  self.image_ref,
                                                  flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Invalid flavorRef provided."
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_not_specify_flavor(self):
        """Ensure return error code 400 when not specify flavor"""
        print """

        test_create_servers_not_specify_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     meta=meta,
                                                     accessIPv4=accessIPv4,
                                                     accessIPv6=accessIPv6,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        msg = "Missing flavorRef attribute"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_networks(self):
        print """

        test_create_servers_specify_not_exists_networks

        """
        uuid = '12345678-90ab-cdef-fedc-ba0987654321'
        sql = "select uuid from networks where uuid = '" + uuid + "';"
        rs = self.get_data_from_mysql(sql)
        self.assertEqual(0, len(rs))

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.1.1',
                     'uuid':uuid}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     networks=networks,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        msg = ("NetworkNotFoundForUUID: Network could not be found "
               "for uuid 12345678-90ab-cdef-fedc-ba0987654321")
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_create_servers_specify_keypair(self):
        print """

        test_create_servers_specify_keypair

        """

        # create keypair
        keyname = rand_name('key')
        resp, keypair = self.kp_client.create_keypair(keyname)
        resp, body = self.os.keypairs_client.list_keypairs()

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server_kw(name=name,
                                                       imageRef=self.image_ref,
                                                       flavorRef=self.flavor_ref,
                                                       metadata=meta,
                                                       key_name=keyname,
                                                       personality=personality)
        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])
        self.assertEqual(keyname, server['key_name'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.get_server(server['id'])
        print "body=", body
        self.assertEqual(keyname, body['key_name'])

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_keypair(self):
        print """

        test_create_servers_specify_not_exists_keypair

        """

        # create keypair
        keyname = rand_name('key')
#        resp, keypair = self.kp_client.create_keypair(keyname)
#        resp, body = self.os.keypairs_client.list_keypairs()

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     key_name=keyname,
                                                     personality=personality)
        print "resp=", resp
        print "body=", body
        msg = "Invalid key_name provided."
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_get_server_details_by_id(self):
        """Ensure details of a specific server by ID."""
        print """

        test_get_server_details_by_id

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

        resp, body = self.ss_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(name, body['name'])

    @attr(kind='medium')
    def test_get_server_details_by_uuid(self):
        """Ensure details of a specific server by UUID."""
        print """

        test_get_server_details_by_uuid

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

        resp, body = self.ss_client.get_server(server['id'])

        uuid = body['uuid']

        resp, body = self.ss_client.get_server(uuid)
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(server['id'], body['id'])

    @attr(kind='medium')
    def test_get_server_details_by_not_exists_id(self):
        """Ensure return error response Code 404"""
        print """

        test_get_server_details_by_not_exists_id

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

        self.assertNotEqual(99, server['id'])
        resp, body = self.ss_client.get_server(99)
        print "resp=", resp
        print "body=", body

        msg = "The resource could not be found."
        self.assertEqual('404', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_update_server(self):
        """updates the editable attributes of a server"""
        print """

        test_update_server

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

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name, body['name'])

        alt_name = rand_name('server')
        self.assertNotEqual(name, alt_name)

        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_update_server_not_exists_id(self):
        """Ensure return error response Code 404"""
        print """

        test_update_server_not_exists_id

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

        alt_name = rand_name('server')
        self.assertNotEqual(name, alt_name)
        self.assertNotEqual(99, server['id'])
        resp, body = self.ss_client.update_server(99, name=alt_name)
        print "resp=", resp
        print "body=", body

        msg = "The resource could not be found."
        self.assertEqual('404', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_update_server_same_name(self):
        """updates the editable attributes of a server"""
        print """

        test_update_server_same_name

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name1 = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name1,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        name2 = rand_name('server')
        resp, server = self.ss_client.create_server(name2,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name2, body['name'])

        alt_name = name1
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_update_server_empty_name(self):
        """Ensure return error response Code 400"""
        print """

        test_update_server_empty_name

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

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name, body['name'])

        alt_name = ''
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        msg = "Server name is an empty string"
        self.assertEqual('400', resp['status'])
        self.assertTrue(msg in body)

    @attr(kind='medium')
    def test_delete_server(self):
        """delete server instance from the system"""
        print """

        test_delete_server

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

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_not_exists_id(self):
        """Ensure return error response Code 404"""
        print """

        test_delete_server_not_exists_id

        """
        resp = self.ss_client.delete_server(99)
        print "resp=", resp
        self.assertEqual('404', resp[0]['status'])
        msg = 'The resource could not be found.'
        self.assertTrue(msg in resp[1])

    @attr(kind='medium')
    def test_delete_server_when_server_is_building(self):
        """delete server when server is building"""
        print """

        test_delete_server_when_server_is_building

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

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_when_server_is_deleting(self):
        """delete server when server is deleting"""
        print """

        test_delete_server_when_server_is_deleting

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

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_when_server_is_deleted(self):
        """return error response Code 404 when server is deleted"""
        print """

        test_delete_server_when_server_is_deleted

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

        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('404', resp['status'])
