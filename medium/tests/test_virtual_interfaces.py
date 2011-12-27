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
import subprocess
import sys
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from kong import tests
from storm import openstack
import storm.config
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
#    environ_processes = module.environ_processes
    config = module.config


def tearDownModule(module):
    pass


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

    def tearDown(self):
        # kill still existing virtual instances.
        print """

        Terminate All Instances

        """
        try:
            _, servers = self.os.servers_client.list_servers()
            print "Servers : %s" % servers
            for s in servers['servers']:
                try:
                    print "Find existing instance %s" % s['id']
                    resp, body = self.os.servers_client.delete_server(s['id'])
                    if resp['status'] in ('204', '202', '200'):
                        self.os.servers_client.wait_for_server_not_exists(
                                                                    s['id'])
                except Exception as e:
                    print e
        except Exception:
            pass
        print """

        Cleanup DB

        """
#        self.output_eventlog()

    def exec_sql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -Ns -e "' + sql + '"'
        results = subprocess.check_output(exec_sql % (
                                          self.config.mysql.user,
                                          self.config.mysql.password),
                                          shell=True)
        print 'results=' + str(results)
        return [tuple(result.split('\t'))
                    for result in results.split('\n') if result]


class VirtualInterfacesTest(FunctionalTest):
    def setUp(self):
        super(VirtualInterfacesTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_server_id_is_valid(self):
        """Returns 200 response with a list of virtual interfaces"""

        # create a network for test
        networks = []
        cidr = '10.0.10.0/24'
        subprocess.check_call('bin/nova-manage network create '
                              '--label=label-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=%s '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ' % cidr,
                              cwd=self.config.nova.directory, shell=True)
        sql = 'SELECT dhcp_start, uuid, gateway FROM networks ' + \
              'WHERE cidr = \'%s\';' % cidr
        network_fixed_ip, network_uuid, network_gw = self.exec_sql(sql)[0]
        network_fixed_ip = '10.0.10.100'
        networks.append({'fixed_ip': network_fixed_ip,
                         'uuid': network_uuid})

        # create a server with a virtual_interface for test
        name = 'server_' + self._testMethodName
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality,
                                                    networks=networks)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.ss_client.list_server_virtual_interfaces(
                                                            server['id'])
        self.assertEqual('200', resp['status'])
        vifs = body['virtual_interfaces']
        self.assertEqual(True, len(vifs) >= 1)
        self.assertTrue(vifs[0]['id'])
        self.assertTrue(vifs[0]['mac_address'])

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_server_uuid_is_valid(self):
        """Returns 200 response with a list of virtual interfaces"""

        # create a network for test
        networks = []
        cidr = '10.0.4.0/24'
        subprocess.check_call('bin/nova-manage network create '
                              '--label=label-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=%s '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ' % cidr,
                              cwd=self.config.nova.directory, shell=True)
        sql = 'SELECT dhcp_start, uuid, gateway FROM networks ' + \
              'WHERE cidr = \'%s\';' % cidr
        network_fixed_ip, network_uuid, network_gw = self.exec_sql(sql)[0]
        network_fixed_ip = '10.0.4.100'
        networks.append({'fixed_ip': network_fixed_ip,
                         'uuid': network_uuid})

        # create a server with a virtual_interface for test
        name = 'server_' + self._testMethodName
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality,
                                                    networks=networks)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.ss_client.list_server_virtual_interfaces(
                                                            server['uuid'])
        self.assertEqual('200', resp['status'])
        vifs = body['virtual_interfaces']
        self.assertEqual(True, len(vifs) >= 1)
        self.assertTrue(vifs[0]['id'])
        self.assertTrue(vifs[0]['mac_address'])

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_not_found_with_server_id(self):
        """Returns 404 response"""
        # make sure no record in db
        try:
            subprocess.check_call('mysql -u %s -p%s -D nova -e "'
                              'DELETE FROM virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
        except Exception:
            pass

        # execute and assert
        server_id = sys.maxint  # not found
        resp, body = self.ss_client.list_server_virtual_interfaces(server_id)
        self.assertEqual('404', resp['status'])
        error = body['itemNotFound']
        self.assertEqual('The resource could not be found.', error['message'])
        self.assertEqual(404, error['code'])

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_not_found_with_server_uuid(self):
        """Returns 404 response"""
        # make sure no record in db
        try:
            subprocess.check_call('mysql -u %s -p%s -D nova -e "'
                              'DELETE FROM virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
        except Exception:
            pass

        # execute and assert
        server_uuid = '99999999-9999-9999-9999-999999999999'  # not found
        resp, body = self.ss_client.list_server_virtual_interfaces(server_uuid)
        self.assertEqual('404', resp['status'])
        error = body['itemNotFound']
        self.assertEqual('The resource could not be found.', error['message'])
        self.assertEqual(404, error['code'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #xxx')
    def test_list_virtual_interfaces_when_server_id_is_empty_string(self):
        """Returns 400 response"""
        # make sure no record in db
        subprocess.check_call('mysql -u %s -p%s -D nova -e "'
                              'DELETE FROM virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        # execute and assert
        server_id = ''
        resp, body = self.ss_client.list_server_virtual_interfaces(server_id)
        self.assertEqual('400', resp['status'])

    @test.skip_test('can not filter virtual_interfaces')
    @attr(kind='medium')
    def test_list_virtual_interfaces_when_network_amount_is_zero(self):
        """Returns 200 response with an empty list"""
        subprocess.check_call('mysql -u %s -p%s -D nova -e "'
                      'DELETE FROM virtual_interfaces;'
                      '"' % (
                          self.config.mysql.user,
                          self.config.mysql.password),
                      shell=True)

        # create a server with a virtual_interface for test
        name = 'server_' + self._testMethodName
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.ss_client.list_server_virtual_interfaces(
                                                            server['id'])
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['virtual_interfaces'])

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_network_amount_is_one(self):
        """Returns 200 response with a list of virtual interfaces"""
        # create a network for test
        networks = []
        cidr = '10.0.5.0/24'
        subprocess.check_call('bin/nova-manage network create '
                              '--label=label-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=%s '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ' % cidr,
                              cwd=self.config.nova.directory, shell=True)
        sql = 'SELECT dhcp_start, uuid, gateway FROM networks ' + \
              'WHERE cidr = \'%s\';' % cidr
        network_fixed_ip, network_uuid, network_gw = self.exec_sql(sql)[0]
        network_fixed_ip = '10.0.5.100'
        networks.append({'fixed_ip': network_fixed_ip,
                         'uuid': network_uuid})

        # create a server with a virtual_interface for test
        name = 'server_' + self._testMethodName
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality,
                                                    networks=networks)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.ss_client.list_server_virtual_interfaces(
                                                            server['id'])
        self.assertEqual('200', resp['status'])
        vifs = body['virtual_interfaces']
        self.assertEqual(True, len(vifs) >= 1)
        self.assertTrue(vifs[0]['id'])
        self.assertTrue(vifs[0]['mac_address'])

    @attr(kind='medium')
    def test_list_virtual_interfaces_when_network_amount_is_three(self):
        """Returns 200 response with a list of virtual interfaces"""

        # create three networks for test
        cidrs = ['10.0.6.0/24', '10.0.7.0/24', '10.0.8.0/24']
        networks = []
        for cidr in cidrs:
            subprocess.check_call('bin/nova-manage network create '
                                  '--label=label-1 '
                                  '--project_id=1 '
                                  '--fixed_range_v4=%s '
                                  '--bridge_interface=br-int '
                                  '--num_networks=1 '
                                  '--network_size=32 ' % cidr,
                                  cwd=self.config.nova.directory, shell=True)
            sql = 'SELECT dhcp_start, uuid, gateway FROM networks ' + \
                  'WHERE cidr = \'%s\';' % cidr
            network_fixed_ip, network_uuid, network_gw = self.exec_sql(sql)[0]
            network_fixed_ip = '.'.join(network_fixed_ip.split('.')[0:3])\
                                    + '.100'
            networks.append({'fixed_ip': network_fixed_ip,
                             'uuid': network_uuid})

        # create a server with virtual_interfaces for test
        name = 'server_' + self._testMethodName
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality,
                                                    networks=networks)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.ss_client.list_server_virtual_interfaces(
                                                            server['id'])
        self.assertEqual('200', resp['status'])
        vifs = body['virtual_interfaces']
        self.assertEqual(True, len(vifs) >= 3)
