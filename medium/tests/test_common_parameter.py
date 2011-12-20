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
from storm.common import rest_client_unauth
from storm import exceptions
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

    try:
        # create users.
        subprocess.check_call('bin/nova-manage user create '
                              '--name=admin --access=secrete --secret=secrete',
                              cwd=config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage user create '
                              '--name=demo --access=secrete --secret=secrete',
                              cwd=config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('bin/nova-manage project create '
                              '--project=1 --user=admin',
                              cwd=config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage project create '
                              '--project=2 --user=demo',
                              cwd=config.nova.directory, shell=True)

        # allocate networks.
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_1-1 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.0.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_1-2 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.1.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_2-1 '
                              '--project_id=2 '
                              '--fixed_range_v4=10.0.2.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=config.nova.directory, shell=True)

    except Exception:
        pass


def tearDownModule(module):
    pass


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

    def tearDown(self):
        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            (id, name, state) = line.split()
            if state == 'running':
                subprocess.check_call('virsh destroy %s' % id, shell=True)
            subprocess.check_call('virsh undefine %s' % name, shell=True)

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


class ApiCommonParameterTest(FunctionalTest):
    def setUp(self):
        super(ApiCommonParameterTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
#        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_auth_token_not_exist(self):
        """If token is no exist and return 401"""
        print """

        test_auth_token_not_exist

        """
        self.ss_client.client.token = "notexist1234567890"
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('401', resp['status'])
        self.assertEqual(True, body.find('Unauthorized') >= 0)

    @attr(kind='medium')
    def test_auth_token_empty(self):
        """If token is empty and return 401"""
        print """

        test_auth_token_empty

        """
        self.ss_client.client.token = ""
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('401', resp['status'])
        self.assertEqual(True, body.find('Unauthorized') >= 0)

    @attr(kind='medium')
    def test_auth_token_without(self):
        """If token is empty and return 401"""
        print """

        test_auth_token_without

        """
        conf = self.ss_client.config
        unauth_client = rest_client_unauth.RestClientUnauth(
                                                conf.nova.username,
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                conf.nova.tenant_name,
                                                config=conf)
        method = 'GET'
        url = 'servers'
        resp, body = unauth_client.request_without_token(method, url)
        print '=========================S'
        print "resp=", resp
        print "body=", body
        print '=========================E'
        self.assertEqual('401', resp['status'])
        self.assertEqual(True, body.find('Unauthorized') >= 0)

    @test.skip_test('wait large test')
    @attr(kind='medium')
    def test_method_unknown(self):
        """If method is unknown then return 404"""
        print """

        test_method_unknown

        """
        conf = self.ss_client.config
        unauth_client = rest_client_unauth.RestClientUnauth(
                                                conf.nova.username,
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                conf.nova.tenant_name,
                                                config=conf)
        method = 'UNKNOWN'
        url = 'servers'
        resp, body = unauth_client.request(method, url)
        print '=========================S'
        print "resp=", resp
        print "body=", body
        print '=========================E'
        self.assertEqual('405', resp['status'])
#        self.assertEqual(True, body.find('Not Found') >= 0)

    @test.skip_test('wait large test')
    @attr(kind='medium')
    def test_post_body_not_json(self):
        """if post request with no-json format body, return 400"""
        print """

        test_post_body_not_json

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]

        post_body = {
            'name': name,
            'imageRef': self.image_ref,
            'flavorRef': self.flavor_ref,
        }

        post_body['metadata'] = meta
        post_body['personality'] = personality
        post_body['accessIPv4'] = accessIPv4
        post_body['accessIPv6'] = accessIPv6
#        post_body = json.dumps({'server': post_body})
        post_body = str({'server': post_body})

        #self.assertRaises(exceptions.BadRequest,
        resp, body = self.ss_client.client.post('servers', post_body,
                                                  self.ss_client.headers)
        self.assertEqual('415', resp['status'])

    @attr(kind='medium')
    def test_tenant_empty(self):
        """If tenant is empty and return 200 without access url"""
        print """

        test_tenant_empty

        """
        conf = self.ss_client.config
        try:
            unauth_client = rest_client_unauth.RestClientUnauth(
                                                conf.nova.username,
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                '',
                                                config=conf)
        except KeyError:
            pass

        self.assertEqual('', unauth_client.base_url)
        self.assertNotEqual(None, unauth_client.token)

    @attr(kind='medium')
    def test_tenant_empty_noadmin(self):
        """If tenant is not specified and return 200 without access url"""
        print """

        test_tenant_empty_noadmin

        """
        conf = self.ss_client.config
        try:
            unauth_client = rest_client_unauth.RestClientUnauth(
                                                'demo',
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                '',
                                                config=conf)
        except KeyError:
            pass

        self.assertEqual('', unauth_client.base_url)
        self.assertNotEqual(None, unauth_client.token)

    @attr(kind='medium')
    def test_tenant_without_key(self):
        """If tenant is not specified and return 200 without access url"""
        print """

        test_tenant_without_key

        """
        conf = self.ss_client.config
        try:
            unauth_client = rest_client_unauth.RestClientUnauth(
                                                conf.nova.username,
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                None,
                                                config=conf)
        except KeyError:
            pass

        self.assertEqual('', unauth_client.base_url)
        self.assertNotEqual(None, unauth_client.token)

    @attr(kind='medium')
    def test_tenant_not_exist(self):
        """If tenant is not exist and return 200 without access url"""
        print """

        test_tenant_not_exist

        """
        conf = self.ss_client.config
        try:
            unauth_client = rest_client_unauth.RestClientUnauth(
                                                conf.nova.username,
                                                conf.nova.api_key,
                                                conf.nova.auth_url,
                                                'notexisttenant',
                                                config=conf)
        except KeyError:
            pass

        self.assertEqual('', unauth_client.base_url)
        self.assertEqual('401', unauth_client.token)
