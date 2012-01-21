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
import os
import base64
import re
import subprocess
import time
import json
import logging
import inspect

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
from kong import tests
from storm import openstack
from storm.common import rest_client
from storm.common.rest_client import LoggingFeature
from storm.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

# Configuration values for scenario test
# number of instance to boot up this scenario.
NUM_OF_INSTANCE = 2
# using flavor on this scenario.
FLAVORS = {1,2}
# created user on this scenario.
USER = "test_user2"
PASSWORD = "password"
# created tenant on this scenaro.
TENANT = "tenant2"

LOG = logging.getLogger("large.tests.test_scenario")
messages = []



def setUpModule(module):
    rest_client.logging = ScenarioLogging()

def tearDownModule(module):
    print "\nScenario execution done."
    for m in messages:
        print "Process: %s\n Result %s" % m

class ScenarioLogging(LoggingFeature):

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
        self.default_config = storm.config.StormConfig('etc/large.conf')
        self._load_client(self.default_config)

    def tearDown(self):
        self.data.teardown_all()

    def swap_user(self, user, password, tenant_name):
        config = storm.config.StormConfig('etc/large.conf')
        config.keystone.conf.set('keystone', 'user', user)
        config.keystone.conf.set('keystone', 'password', password)
        config.keystone.conf.set('keystone', 'tenant_name', tenant_name)
        self._load_client(config)

    def _load_client(self, config):
        self.os = openstack.Manager(config)
        self.keystone_client = self.os.keystone_client
        self.token_client = TokenClient(config)
        self.keypair_client = self.os.keypairs_client
        self.server_client = self.os.servers_client
        self.images_client = self.os.images_client
        self.quantum_client = self.os.quantum_client
        self.db = DBController(config)
        token = self.token_client.get_token(config.keystone.user,
                                            config.keystone.password,
                                            config.keystone.tenant_name)        
        self.glance = GlanceWrapper(token, self.default_config)
        self.data = DataGenerator(self.keystone_client,
                                  self.token_client,
                                  self.keypair_client,
                                  self.server_client,
                                  self.images_client,
                                  self.quantum_client,
                                  self.glance)

class DBController(object):
    def __init__(self, config):
        self.config = config

    def exec_mysql(self, sql, service):
        LOG.debug("Execute sql %s" % sql)
        exec_sql = 'mysql -h %s -u %s -p%s %s -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.host,
                                         self.config.mysql.user,
                                         self.config.mysql.password,
                                         service),
                                         shell=True)
        LOG.debug("SQL Execution Result %s" % result)


class DataGenerator(object):
    def __init__(self, keystone_client,
                       token_client,
                       keypair_client,
                       server_client,
                       images_client,
                       quantum_client,
                       glance):
        self.keystone_client = keystone_client
        self.token_client = token_client
        self.keypair_client = keypair_client
        self.server_client = server_client
        self.images_client = images_client
        self.quantum_client = quantum_client
        self.glance = glance
        self.users = []
        self.tenants = []
        self.roles = []
        self.role_name = None
        self.keypairs = []
        self.images = []
        self.l2 = []
        

    def setup_one_user(self):
        _, tenant = self.keystone_client.create_tenant(TENANT, "tenant_for_test")
        _, user = self.keystone_client.create_user(USER, PASSWORD, tenant['tenant']['id'], USER + "@mail.com")
        self.tenants.append(tenant['tenant'])
        self.users.append(user['user'])

    def setup_role(self):
        _, services = self.keystone_client.get_services()
        services = services['OS-KSADM:services']
        for service in services:
            service_name = service['name']
            service_id = service['id']
            _, roles = self.keystone_client.create_role(service_name + ':test1' , 'Test role', service_id)
            self.role_name = service_name + ':test1'
            self.roles.append(roles['role'])

    def add_image(self, image_name, image_format, container_format, image_file):
        image_id = self.glance.add(image_name, image_format, container_format, image_file)
        self.images.append(image_id)
        return image_id

    def add_keypair(self, keypair_name):
        self.keypair_client.create_keypair(keypair_name)
        self.keypairs.append(keypair_name)

    def create_network(self, name):
        _, body =self.quantum_client.create_network("test_network", 'nova_id')
        network = body['network']
        self.l2.append(network['id'])
        return network['id']

    def teardown_all(self):
        for u in self.users:
            self.keystone_client.delete_user(u['id'])
        for t in self.tenants:
            self.keystone_client.delete_tenant(t['id'])
        for r in self.roles:
            self.keystone_client.delete_role(r['id'])
        for i in self.images:
            self.glance.delete(i)
        for k in self.keypairs:
            self.keypair_client.delete_keypair(k)
#        for n in self.l2:
#            self.quantum_client.delete_network(n)


class NetworkWrapper(object):
    def __init__(self, config):
        self.path = config.nova.directory
    
    def _nova_manage_network(self, action, params):
        cmd = "bin/nova-manage network %s %s" % (action, params)
        print "Running command %s" % cmd
        result = subprocess.check_output(cmd, cwd=self.path, shell=True)
        return result

    def create_network(self, label, ip_range, size, bridge, tenant, uuid, gw, dhcp):
        params = "--label=%s --fixed_range_v4=%s --num_networks=1 --network_size=%s\
 --bridge_interface=%s --project_id=%s --uuid=%s --gateway=%s --dhcp_server=%s" %\
         (label, ip_range, size, bridge, tenant, uuid, gw, dhcp)
        return self._nova_manage_network('create', params)

    def delete_network(self, uuid):
        params = "--uuid=%s" % uuid
        return self._nova_manage_network('delete', params)


class GlanceWrapper(object):
    def __init__(self, token, config):
        self.path = config.glance.directory
        self.conf = config.glance.api_config
        self.host = config.glance.host
        self.port = config.glance.port
        self.token = token
    
    def _glance(self, action, params, yes=None):
        cmd = "glance -A %s -H %s -p %s %s %s" %\
             (self.token, self.host, self.port, action, params)
        print "Running command %s" % cmd
        if yes:
            cmd = ("yes %s|" % yes) + cmd
        result = subprocess.check_output(cmd, cwd=self.path, shell=True)
        return result

    def index(self):
        result = self._glance('index', '', yes="y")
        return result
    
    def add(self, image_name, image_format, container_format, image_file):
        params = "name=%s is_public=true disk_format=%s container_format=%s < %s" \
                      % (image_name,
                        image_format,
                        container_format,
                        os.path.join(os.getcwd(), image_file))
        result = self._glance('add', params)
        # parse add new image ID: <image_id>
        if result:
            splited = str(result).split()
            return splited[splited.count(splited)-1]

    def delete(self, image_id):
        result = self._glance('delete', image_id, yes="y")
        if result:
            return image_id

    def detail(self, image_name):
        params = "name=%s" % image_name
        result = self._glance('details', params, yes='y')
        return result

    def update(self, image_id, image_name):
        params = "%s name=%s" % (image_id, image_name)
        result = self._glance('update', params)
        return result
        
class ScenarioTest(FunctionalTest):

    def test_scenario_check_setups(self):
        # create new uses
        self.data.setup_one_user()
        self.data.setup_role()
        # create glance image.
        token = self.token_client.get_token(USER, PASSWORD, TENANT)
        glance = GlanceWrapper(token, self.default_config)
        new_image_id = glance.add("test_scenario1", "ami", "ami", "etc/images/tty.img")
        print new_image_id
        # check setuped image.
        print glance.index()
        print glance.detail('test_scenario1')
        print glance.update(new_image_id, "updated_image01")
        print glance.detail('updated_image01')
        # remove image.
        print glance.delete(new_image_id)
        # remove user and tenants in teardown.

    def _application_tenant(self, scenario):
        results = []
        # create new uses
        self.data.setup_one_user()
        self.data.setup_role()
        # create glance image.
        fw_image = self.data.add_image(scenario + "_FW", 'ami', 'ami', "etc/images/tty.img")
        lb_image = self.data.add_image(scenario + "_LB", 'ami', 'ami', "etc/images/tty.img")
        server_image = self.data.add_image(scenario + "_Server", 'ami', 'ami', "etc/images/tty.img")
        # create keypair
        self.data.add_keypair(scenario + "_keypair")
        # create L2 network.
        self.data.create_network(scenario)
        
    def test_scenario_application_new_tenant(self):
        uuid = self.data.create_network('test')
        wrapper = NetworkWrapper(self.default_config)
        wrapper.create_network('test1', '10.1.3.0/24', '256', 'br_int', 'prjAdmin', uuid, '10.1.3.255', '10.1.3.2')

#        self._application_tenant("scenario1")
        