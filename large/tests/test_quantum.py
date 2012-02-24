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
import logging
import inspect
import uuid

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
from kong import tests
from storm import openstack
from storm.common import rest_client
from storm.common.rest_client import LoggingFeature
from storm.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

LOG = logging.getLogger("large.tests.test_keystone")
messages = []


def setUpModule(module):
    rest_client.logging = QuantumLogging()


def tearDownModule(module):
    print "\nAll Quantum tests done. Dump message infos."
    for m in messages:
        print "Test: %s\nMessages %s" % m


class QuantumLogging(LoggingFeature):

    def do_auth(self, creds):
        LOG.info("Authenticate %s" % creds)

    def do_request(self, req_url, method, headers, body):
        LOG.info(">>> Send Request %s %s" % (method, req_url))
        LOG.debug(">>> Headers %s" % headers)
        LOG.debug(">>> Request Body %s" % body)

    def do_response(self, resp, body):
        LOG.info("<<< Receive Response %s" % resp)
        LOG.debug("<<< Response Body %s" % body)


class FunctionalTest(unittest.TestCase):

    def setUp(self):
        default_config = storm.config.StormConfig('etc/large.conf')
        self.os = openstack.Manager(default_config)
        self.client = self.os.quantum_client
        self.keystone_client = self.os.keystone_client
        self.token_client = TokenClient(default_config)
        self.data = DataGenerator(self.keystone_client, self.client)
        self.data.setup_one_user()
        self.swap_user('test_quantum_user1', 'password',
                       'test_quantum_tenant1')

    def tearDown(self):
        self.data.teardown_all()

    @attr(kind='large')
    def swap_user(self, user, password, tenant_name):
        config = storm.config.StormConfig('etc/large.conf')
        config.keystone.conf.set('keystone', 'user', user)
        config.keystone.conf.set('keystone', 'password', password)
        config.keystone.conf.set('keystone', 'tenant_name', tenant_name)
        self.os = openstack.Manager(config)
        self.keystone_client = self.os.keystone_client
        self.client = self.os.quantum_client


class DataGenerator(object):
    def __init__(self, client, quantum):
        self.client = client
        self.quantum = quantum
        self.users = []
        self.tenants = []
        self.roles = []
        self.networks = []
        self.vifs = []
        self.role_name = None

    def setup_one_user(self):
        _, tenant = self.client.create_tenant("test_quantum_tenant1",
                                              "tenant_for_test")
        _, user = self.client.create_user("test_quantum_user1", "password",
                                          tenant['tenant']['id'],
                                          "user_quantum1@mail.com")
        self.tenants.append(tenant['tenant'])
        self.users.append(user['user'])

    def setup_role(self):
        _, services = self.client.get_services()
        services = services['OS-KSADM:services']
        service_name = services[0]['name']
        service_id = services[0]['id']
        _, roles = self.client.create_role(service_name + ':test1',
                                           'Test role', service_id)
        self.role_name = service_name + ':test1'
        self.roles.append(roles['role'])

    def add_network(self, network):
        self.networks.append(network)

    def add_vif(self, network_id, port_id):
        self.vifs.append((network_id, port_id))

    def teardown_all(self):
        for u in self.users:
            self.client.delete_user(u['id'])
        for t in self.tenants:
            self.client.delete_tenant(t['id'])
        for r in self.roles:
            self.client.delete_role(r['id'])
        for vif in self.vifs:
            self.quantum.detach_port(vif[0], vif[1])
        for n in self.networks:
            self.quantum.delete_network(n['id'])


class QuantumTest(FunctionalTest):

    @attr(kind='large')
    def test_create_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        self.assertTrue(nw['id'] is not None)
        messages.append(('test_create_network', body))

    @attr(kind='large')
    def test_create_network_over_40(self):
        _, body = self.client.create_network('A' * 40 + 'B', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        self.assertTrue(nw['id'] is not None)
        messages.append(('test_create_network_over_40', body))

    @tests.skip_test("Empty network name is allowed")
    @attr(kind='large')
    def test_create_network_empty_name(self):
        _, body = self.client.create_network('', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        self.assertTrue(nw['id'] is not None)
        messages.append(('test_create_network_empty_name', body))

    @tests.skip_test("Duplicate network entry is allowed")
    @attr(kind='large')
    def test_create_network_duplicate(self):
        _, body = self.client.create_network('name', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        resp, body = self.client.create_network('name', 'nova_id')
        self.assertEqual('409', resp['status'])
        messages.append(('test_create_network_duplicate', body))

    @attr(kind='large')
    def test_delete_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        resp, body = self.client.delete_network(nw['id'])
        self.assertEqual('204', resp['status'])
        messages.append(('test_delete_network', body))

    @attr(kind='large')
    def test_delete_network_not_exists(self):
        """
        It seems response status code is not valid.
        """
        resp, body = self.client.delete_network('0000-0000-0000-0000')
        self.assertEqual('420', resp['status'])
        messages.append(('test_delete_network_not_exists', body))

    @attr(kind='large')
    def test_list_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.list_network()
        networks = body['networks']
        self.assertIn(nw['id'], [n['id'] for n in networks])
        messages.append(('test_list_network', body))

    @attr(kind='large')
    def test_list_detail_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.detail_networks()
        networks = body['networks']
        self.assertIn('new_network', [n['name'] for n in networks])
        messages.append(('test_list_datail_network', body))

    @attr(kind='large')
    def test_create_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        self.assertTrue(body is not None)
        messages.append(('test_create_port', body))

    @attr(kind='large')
    def test_create_port_none_exist_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        resp, body = self.client.create_port('0000-0000-0000-0000', 'nova')
        self.assertEqual('420', resp['status'])
        messages.append(('test_create_port_none_exist_network', body))

    @attr(kind='large')
    def test_delete_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        resp, body = self.client.delete_port(nw['id'], port['id'])
        self.assertEqual('204', resp['status'])
        messages.append(('test_delete_port', body))

    @attr(kind='large')
    def test_delete_port_none_exist_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        resp, body = self.client.delete_port(nw['id'], 'non_exist_port')
        self.assertEqual('430', resp['status'])
        messages.append(('test_delete_port_none_exist_port', body))

    @attr(kind='large')
    def test_list_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        _, body = self.client.list_ports(nw['id'])
        ports = body['ports']
        self.assertIn(port['id'], [n['id'] for n in ports])
        messages.append(('test_list_port', body))

    @attr(kind='large')
    def test_list_port_with_none_exist_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        resp, body = self.client.list_ports('none_exist_network')
        self.assertEqual('420', resp['status'])
        messages.append(('test_list_port_with_none_exist_network', body))

    @attr(kind='large')
    def test_list_port_details(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        _, body = self.client.list_port_details(nw['id'])
        ports = body['ports']
        self.assertIn(port['id'], [n['id'] for n in ports])
        messages.append(('test_list_port_details', body))

    @attr(kind='large')
    def test_list_port_details_with_not_exist_network(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        resp, body = self.client.list_port_details('none_exist_network')
        self.assertEqual('420', resp['status'])
        messages.append('test_list_port_details_with_not_exist_network', body)

    @attr(kind='large')
    def test_attach_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        vif = str(uuid.uuid4())
        resp, body = self.client.attach_port(nw['id'], port['id'], vif)
        self.data.add_vif(nw['id'], port['id'])
        self.assertEqual('204', resp['status'])
        messages.append(('test_attach_port', body))

    @attr(kind='large')
    def test_attach_port_already_attached(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        vif = str(uuid.uuid4())
        resp, body = self.client.attach_port(nw['id'], port['id'], vif)
        self.data.add_vif(nw['id'], port['id'])
        resp, body = self.client.attach_port(nw['id'], port['id'], vif)
        self.assertEqual('432', resp['status'])
        messages.append(('test_attach_port_already_attached', body))

    @attr(kind='large')
    def test_detach_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        vif = str(uuid.uuid4())
        _, body = self.client.attach_port(nw['id'], port['id'], vif)
        resp, body = self.client.detach_port(nw['id'], port['id'])
        self.data.add_vif(nw['id'], port['id'])
        self.assertEqual('204', resp['status'])
        messages.append(('test_detach_port', body))

    @attr(kind='large')
    def test_detach_port_with_no_attached(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        resp, body = self.client.detach_port(nw['id'], port['id'])
        self.data.add_vif(nw['id'], port['id'])
        self.assertEqual('204', resp['status'])
        messages.append(('test_detach_port_with_no_attached', body))

    @attr(kind='large')
    def test_list_attach_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        vif = str(uuid.uuid4())
        _, body = self.client.attach_port(nw['id'], port['id'], vif)
        self.data.add_vif(nw['id'], port['id'])
        _, body = self.client.list_port_attachment(nw['id'], port['id'])
        attachment = body['attachment']
        self.assertEqual(vif, attachment['id'])
        messages.append(('test_list_attach_port', body))

    @attr(kind='large')
    def test_list_attach_port_with_no_attach(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        port = body['port']
        _, body = self.client.list_port_attachment(nw['id'], port['id'])
        attachment = body['attachment']
        self.assertEqual({}, attachment)
        messages.append(('test_list_attach_port_with_no_attach', body))

    @attr(kind='large')
    def test_list_attach_port_with_non_exist_port(self):
        _, body = self.client.create_network('new_network', 'nova_id')
        nw = body['network']
        self.data.add_network(nw)
        _, body = self.client.create_port(nw['id'], 'nova')
        resp, body = self.client.list_port_attachment(nw['id'],
                                                      'non_exist_port')
        self.assertEqual('430', resp['status'])
        messages.append(('test_list_attach_port_with_non_exist_port', body))
