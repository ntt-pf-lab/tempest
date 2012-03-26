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
import logging
import json

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
from storm import openstack
from storm.common import rest_client
from storm.common.rest_client import LoggingFeature
from storm.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

# Configuration values for scenario test

LOG = logging.getLogger("large.tests.test_scenario")
messages = []

# global passord for test users.
PASSWORD = 'password'
# bridge name for networking.
BRIDGE = 'br-int'
# Inner L2 network, bridge, gateway, dhcp
L2_NETWORK = ('10.1.3.0/24', 'br-int', '10.1.3.1', '10.1.3.2') 
# Outer L2 network, bridge, gateway, dhcp
G2_NETWORK = ('172.30.3.0/24', 'br-int', '172.30.3.1', '172.30.3.2')

def setUpModule(module):
    ''' Prerequirement for test
        1. define a user of administrator, and setting it on large.conf
        2. No network definition on nova-network.
        3. kernel and disk image registered on glance
    '''
    rest_client.logging = ScenarioLogging()

def tearDownModule(module):
    print "\nScenario execution done."
    with open(".test_result.json", "w") as file:
        json.dump(messages, file, sort_keys=False, indent=4)

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
        #self.data.teardown_all()
        pass

    def swap_user(self, user, password, tenant_name):
        config = storm.config.StormConfig('etc/large.conf')
        config.keystone.conf.set('keystone', 'user', user)
        config.keystone.conf.set('keystone', 'password', password)
        config.keystone.conf.set('keystone', 'tenant_name', tenant_name)
        config.nova.conf.set('nova', 'user', user)
        config.nova.conf.set('nova', 'api_key', password)
        config.nova.conf.set('nova', 'tenant_name', tenant_name)
        self._load_client(config, data=self.data)

    def _load_client(self, config, data=None):
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
        self.nova_manage_network = NetworkWrapper(self.default_config)
        self.glance = GlanceWrapper(token, self.default_config)
        self.data = DataGenerator(self.keystone_client,
                                  self.token_client,
                                  self.keypair_client,
                                  self.server_client,
                                  self.images_client,
                                  self.quantum_client,
                                  self.nova_manage_network,
                                  self.glance,
                                  data=data)

    def _run_instance(self, name, image):
        meta = {}
        accessIPv4 = ''
        accessIPv6 = ''
        name = name
        flavor_ref = '1'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.server_client.create_server(name,
                                                    image,
                                                    flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.server_client.wait_for_server_status(server['id'], 'ACTIVE')
        return server['id']

    def _list_all_instance(self):
        _, server = self.server_client.list_servers_with_detail()
        return server


    def _terminate_instance(self, server_id):
        self.server_client.delete_server(server_id)
        self.server_client.wait_for_server_not_exists_ignore_error(server_id)


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
                       nova_manage_network,
                       glance,
                       data=None):
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
        self.nw = []
        self.nova_manage_network = nova_manage_network
        self.data = data

    def setup_one_user(self, name):
        _, tenant = self.keystone_client.create_tenant(name + '_tenant', "tenant_for_test")
        _, user = self.keystone_client.create_user(name, PASSWORD, tenant['tenant']['id'], name + "@mail.com")
        self.tenants.append(tenant['tenant']['id'])
        self.users.append(user['user']['id'])
        return {'user': user['user'], 'tenant': tenant['tenant']}

    def setup_role(self):
        result = []
        _, services = self.keystone_client.get_services()
        services = services['OS-KSADM:services']
        for service in services:
            service_name = service['name']
            service_id = service['id']
            _, roles = self.keystone_client.create_role(service_name + ':test1' , 'Test role', service_id)
            self.role_name = service_name + ':test1'
            self.roles.append(roles['role'])
            result.append(roles['role'])
        return {'role':result}

    def add_image(self, image_name, image_format, container_format, image_file, kernel_id=None):
        if kernel_id:
            image_id = self.glance.add_image(image_name, image_format, container_format, image_file, kernel_id)
        else:
            image_id = self.glance.add(image_name, image_format, container_format, image_file)            
        self.images.append(image_id)
        return image_id

    def add_keypair(self, keypair_name):
        self.keypair_client.create_keypair(keypair_name)
        self.keypairs.append(keypair_name)
        return {'keypair': keypair_name}

    def create_network(self, name):
        _, body =self.quantum_client.create_network("test_network", 'nova_id')
        network = body['network']
        self.l2.append(network['id'])
        return network['id']

    def create_ip_block(self, label, ip_range, size, bridge, tenant, uuid, gw, dhcp):
        self.nova_manage_network.create_network(label, ip_range, size, bridge, tenant, uuid, gw, dhcp)
        self.nw.append(uuid)
        return uuid

    def teardown_all(self):
        for i in self.images:
            self.glance.delete(i)
        self.images = []
        for k in self.keypairs:
            self.keypair_client.delete_keypair(k)
        self.keypairs = []
        for n in self.nw:
            self.nova_manage_network.delete_network(n)
        self.nw = []
        for u in self.users:
            self.keystone_client.delete_user(u)
        self.users = []
        for t in self.tenants:
            self.keystone_client.delete_tenant(t)
        self.tenants = []
        for r in self.roles:
            self.keystone_client.delete_role(r['id'])
        self.roles = []
        if self.data:
            self.data.teardown_all()

class NetworkWrapper(object):
    def __init__(self, config):
        self.path = config.nova.directory

    def _nova_manage_network(self, action, params):
        flags = "--flagfile=etc/nova.conf"
        cmd = "bin/nova-manage %s network %s %s" % (flags, action, params)
        print "Running command %s" % cmd
        result = subprocess.check_output(cmd, cwd=self.path, shell=True)
        return result

    def create_network(self, label, ip_range, size, bridge, tenant, uuid, gw, dhcp):
        params = "--label=%s --fixed_range_v4=%s --num_networks=1 --network_size=%s\
 --bridge_interface=%s --project_id=%s --uuid=%s --gateway=%s --dhcp_server=%s --host=xosb1" %\
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
#        print "Running command %s" % cmd
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

    def add_image(self, image_name, image_format, container_format, image_file, kernel_id):
        params = "name=%s is_public=true disk_format=%s container_format=%s kernel_id=%s < %s" \
                      % (image_name,
                        image_format,
                        container_format,
                        kernel_id,
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

    def _application_tenant(self, scenario):
        results = {}
        # create new uses
        results.update(self.data.setup_one_user(scenario))
        self.swap_user(scenario, PASSWORD, scenario + "_tenant")
        # create glance image.
        kernel = self.data.add_image(scenario + "_Kernel", 'aki', 'aki', "etc/images/ttylinux-vmlinuz")
        results.update({'Kernel Image': kernel})
        fw_image = self.data.add_image(scenario + "_FW", 'ami', 'ami', "etc/images/tty.img", kernel)
        results.update({'FW Image': fw_image})
        lb_image = self.data.add_image(scenario + "_LB", 'ami', 'ami', "etc/images/tty.img", kernel)
        results.update({'LB Image': lb_image})
        server_image = self.data.add_image(scenario + "_Server", 'ami', 'ami', "etc/images/tty.img", kernel)
        results.update({'Server Image': server_image})
        # create keypair
        key = self.data.add_keypair(scenario + "_keypair")
        results.update({'Keypair': key})
        # create L2 network.
        nw = self.data.create_network(scenario)
        results.update({'L2 Network': nw})
        # create IP block.
        block = self.data.create_ip_block(scenario, L2_NETWORK[0], 255, L2_NETWORK[1], results['tenant']['id'], nw, L2_NETWORK[2], L2_NETWORK[3])
        results.update({'IP Block': block})
        return results

    def _application_vpn_tenant(self, scenario):
        results = self._application_tenant(scenario)
        # create L2 network.
        nw = self.data.create_network(scenario)
        results.update({'VPN L2 Network': nw})
        # create IP block.
        block = self.data.create_ip_block(scenario, G2_NETWORK[0], 255, G2_NETWORK[1], results['tenant']['id'], nw, G2_NETWORK[2], G2_NETWORK[3])
        results.update({'VPM IP Block': block})
        return results

    @attr(kind='large')
    def test_scenario_application_new_tenant(self):
        '''
        Scenario test for create "Applicate new tenant"
        1. Create new user/tenant
        2. Authorize
        3. Create keypair for user
        4. Create network for tenant
        5. Boot 3 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_tenant("3_scenario_application")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            result['servers'] = self._list_all_instance()
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            messages.append({'scenario':'3_scenario_application', 'result': result})

    @attr(kind='large')
    def test_scenario_delete_tenant(self):
        '''
        Scenario test for create "Delete tenant"
        1. Create new user/tenant
        2. Authorize
        3. Create keypair for user
        4. Create network for tenant
        5. Boot 3 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_tenant("3_scenario_delete")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            result['servers'] = self._list_all_instance()
            self.data.teardown_all()
            messages.append({'scenario':'3_scenario_delete', 'result': result})

    @attr(kind='large')
    def test_scenario_application_new_vpn_tenant(self):
        '''
        Scenario test for create "Applicate new tenant(VPN)"
        1. Create new user/tenant for vpn
        2. Authorize
        3. Create keypair for user
        4. Create network for tenant
        5. Boot 3 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_vpn_tenant("3_scenario_vpn_application")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            result['servers'] = self._list_all_instance()
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            messages.append({'scenario':'3_scenario_vpn_application', 'result': result})

    @attr(kind='large')
    def test_scenario_delete_vpn_tenant(self):
        '''
        Scenario test for create "Delte tenant(VPN)"
        1. Create new user/tenant for vpn
        2. Authorize
        3. Create keypair for user
        4. Create network for tenant
        5. Boot 3 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_vpn_tenant("3_scenario_vpn_delete")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            result['servers'] = self._list_all_instance()
            self.data.teardown_all()
            messages.append({'scenario':'3_scenario_vpn_delete', 'result': result})

    @attr(kind='large')
    def test_scenario_scaleout(self):
        '''
        Scenario test for create "Add VM/Scale out"
        1. Applicate new tenant
          1.1. Create new user/tenant
          1.2. Authorize
          1.3. Create keypair for user
          1.4. Create network for tenant
          1.5. Boot 3 instance for user
        2. Bootup new vm
          2.1. Boot 1 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        scaled = 0
        try:
            setups = self._application_tenant("3_scenario_scaleout")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            scaled = self._run_instance("Scaleout", setups['Server Image'])
            result['servers'] = self._list_all_instance()
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            self._terminate_instance(scaled)
            messages.append({'scenario':'3_scenario_scaleout', 'result': result})

    @attr(kind='large')
    def test_scenario_scaleout_vpn(self):
        '''
        Scenario test for create "Add VM/Scale out"
        1. Applicate new tenant
          1.1. Create new user/tenant
          1.2. Authorize
          1.3. Create keypair for user
          1.4. Create network for tenant
          1.5. Boot 3 instance for user
        2. Bootup new vm
          2.1. Boot 1 instance for user
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        scaled = 0
        try:
            setups = self._application_vpn_tenant("3_scenario_scaleout_vpn")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            scaled = self._run_instance("Scaleout", setups['Server Image'])
            result['servers'] = self._list_all_instance()
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            self._terminate_instance(scaled)
            messages.append({'scenario':'3_scenario_scaleout_vpn', 'result': result})

    @attr(kind='large')
    def test_scenario_snapshot(self):
        '''
        Scenario test for create "Snapshot"
        1. Applicate new tenant
          1.1. Create new user/tenant
          1.2. Authorize
          1.3. Create keypair for user
          1.4. Create network for tenant
          1.5. Boot 3 instance for user
        2. Snapshot VM(Server)
          2.1. Snapshot to VM(Server)
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_tenant("3_scenario_snapshot")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            try:
                # create snapshot.
                resp, _ = self.server_client.create_image(vmserver, 'snapshot')
                alt_img_url = resp['location']
                match = re.search('/images/(?P<image_id>.+)', alt_img_url)
                self.assertIsNotNone(match)
                alt_img_id = match.groupdict()['image_id']
                self.images_client.wait_for_image_status(alt_img_id, 'ACTIVE')
                result['servers'] = self._list_all_instance()
            except:
                raise
            finally:
                pass #self.glance.delete(alt_img_id)
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            messages.append({'scenario':'3_scenario_snapshot', 'result': result})

    @attr(kind='large')
    def test_scenario_snapshot_vpn(self):
        '''
        Scenario test for create "Snapshot"
        1. Applicate new tenant
          1.1. Create new user/tenant
          1.2. Authorize
          1.3. Create keypair for user
          1.4. Create network for tenant
          1.5. Boot 3 instance for user
        2. Snapshot VM(Server)
          2.1. Snapshot to VM(Server)
        '''
        result = {}
        vmfw = 0
        vmlb = 0
        vmserver = 0
        try:
            setups = self._application_vpn_tenant("3_scenario_snapshot_vpn")
            result['setups'] = setups
        except:
            raise
        try:
            # create instances.
            vmfw = self._run_instance("VM_FW", setups['FW Image'])
            vmlb = self._run_instance("VM_LB", setups['LB Image'])
            vmserver = self._run_instance("VM_Server", setups['Server Image'])
            try:
                # create snapshot.
                resp, _ = self.server_client.create_image(vmserver, 'snapshot')
                alt_img_url = resp['location']
                match = re.search('/images/(?P<image_id>.+)', alt_img_url)
                self.assertIsNotNone(match)
                alt_img_id = match.groupdict()['image_id']
                self.images_client.wait_for_image_status(alt_img_id, 'ACTIVE')
                result['servers'] = self._list_all_instance()
            except:
                raise
            finally:
                pass #self.glance.delete(alt_img_id)
        except:
            raise
        finally:
            self._terminate_instance(vmfw)
            self._terminate_instance(vmlb)
            self._terminate_instance(vmserver)
            messages.append({'scenario':'3_scenario_snapshot_vpn', 'result': result})

