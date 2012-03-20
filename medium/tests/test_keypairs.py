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
import time

import unittest2 as unittest
from nose.plugins.attrib import attr
from nova import test

from tempest import openstack
import tempest.config
from tempest.services.nova.json.keypairs_client import KeypairsClient

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess)

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = tempest.config.TempestConfig('etc/medium.conf')
config = default_config
environ_processes = []


def setUpModule(module):
#    environ_processes = module.environ_processes
    config = module.config

    try:
        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D keystone -e "'
                              'DELETE FROM users WHERE name = \'user1\';'
                              'DELETE FROM tenants WHERE name = \'tenant1\';'
                              'DELETE FROM user_roles WHERE NOT EXISTS '
                              '(SELECT * FROM users WHERE id = user_id);'
                              '"' % (
                                  config.mysql.user,
                                  config.mysql.password,
                                  config.mysql.host),
                              shell=True)

        # create tenants.
        subprocess.check_call('bin/keystone-manage tenant add tenant1',
                              cwd=config.keystone.directory, shell=True)

        # create users.
        subprocess.check_call('bin/keystone-manage user add '
                              'user1 user1 tenant1',
                              cwd=config.keystone.directory, shell=True)

        # grant role
        subprocess.check_call('bin/keystone-manage role grant '
                              'Member user1 tenant1',
                              cwd=config.keystone.directory, shell=True)

    except Exception:
        pass


def tearDownModule(module):
    config = module.config

    try:
        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D keystone -e "'
                              'DELETE FROM users WHERE name = \'user1\';'
                              'DELETE FROM tenants WHERE name = \'tenant1\';'
                              'DELETE FROM user_roles WHERE NOT EXISTS '
                              '(SELECT * FROM users WHERE id = user_id);'
                              '"' % (
                                  config.mysql.user,
                                  config.mysql.password,
                                  config.mysql.host),
                              shell=True)

    except Exception:
        pass


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

    def tearDown(self):
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
                    if resp['status'] == '204' or resp['status'] == '202':
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


class KeypairsTest(FunctionalTest):

    def setUp(self):
        super(KeypairsTest, self).setUp()
        self.kp_client = self.os.keypairs_client
        self.ss_client = self.os.servers_client

        class config(object):
            class env(object):
                authentication = "keystone_v2"

            class nova(object):
                build_interval = self.config.nova.build_interval
                build_timeout = self.config.nova.build_timeout

        # user1
        user1 = {'username': 'user1', 'key': 'user1', 'tenant_name': 'tenant1',
                 'auth_url': self.config.nova.auth_url, 'config': config}
        self.kp_client_for_user1 = KeypairsClient(**user1)

        # Please wait, it will fail otherwise.
        time.sleep(5)

    @attr(kind='medium')
    def test_list_keypairs_when_keypair_amount_is_zero(self):
        """Returns 200 response with empty body"""
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

        # execute and assert
        resp, body = self.kp_client.list_keypairs()
        self.assertEqual('200', resp['status'])
        keypairs = body['keypairs']
        self.assertEqual([], keypairs)

    @attr(kind='medium')
    def test_list_keypairs_when_keypair_amount_is_one(self):
        """Returns 200 response with a list of keypairs"""
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

        # create a keypair for test
        keyname = 'key_' + self._testMethodName
        self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.list_keypairs()
        self.assertEqual('200', resp['status'])
        keypairs = body['keypairs']
        self.assertEqual(1, len(keypairs))
        keypair = keypairs[0]['keypair']
        self.assertTrue(keypair['fingerprint'])
        self.assertTrue(keypair['name'])
        self.assertTrue(keypair['public_key'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_list_keypairs_when_keypair_amount_is_three(self):
        """Returns 200 response with a list of keypairs"""
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

        # create three keypairs for test
        keynames = []
        for i in range(0, 3):
            keyname = 'key_' + self._testMethodName + '_' + str(i)
            self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.list_keypairs()
        self.assertEqual('200', resp['status'])
        keypairs = body['keypairs']
        self.assertEqual(3, len(keypairs))
        for keyname in keynames:
            self.assertTrue(keyname in [x['name'] for x in keypairs])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_is_specified(self):
        """Returns 200 response with an information of the created keypair"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('200', resp['status'])
        keypair = body['keypair']
        self.assertTrue(keypair['fingerprint'])
        self.assertTrue(keypair['name'])
        self.assertTrue(keypair['private_key'])
        self.assertTrue(keypair['public_key'])
        self.assertTrue(keypair['user_id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_is_duplicated(self):
        """Returns 409 response"""
        # create a keypair for test
        keyname = 'key_' + self._testMethodName
        self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('409', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_is_empty_string(self):
        """Returns 400 response"""
        # execute and assert
        keyname = ''
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_length_is_over_255(self):
        """Returns 400 response"""
        # execute and assert
        keyname = 'a' * 256
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_keypair_when_keypair_name_is_illegal(self):
        """Returns 400 response"""
        # execute and assert
        keyname = 'key_/.\@:' + self._testMethodName
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_specified(self):
        """Returns 200 response with information of the created keypair"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        publickey = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCefjXKz8NBgmqEXF5' \
                    'gCbiiHcYmHuZ/ZjO497sXvcOsguxLQa+27HjQmg0osIedBgf1AbyBG0' \
                    'gMX7C3muXUHTgiF2QNjhZ6a2ZszmB062rXpL+iC4MEUOFZuzDwzjMGI' \
                    'kLPj/VmwvwCcIuqSxanmJJJo6pD5fUyTh8FC1svd+IwdlspvdsN1jgK' \
                    '8ThRyKo8JbCi+USm/xXuSbg9l/AuQPYy/BXkT5LJWoW3sk9WpqqYit1' \
                    '/dfc4ofRKooj72tkv45+pbglE4GnlB7JQ4Vr03QtW9Z41Dwy7oM1cbq' \
                    'm1lvKYcSvatIeHV7OJE6tj6J/uCjUYY6ZGsghUh5IoP1rTRy7l ' \
                    'openstack@ubuntu'
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('200', resp['status'])
        keypair = body['keypair']
        self.assertTrue(keypair['public_key'])
        self.assertTrue(keypair['user_id'])
        self.assertTrue(keypair['name'])
        self.assertTrue(keypair['fingerprint'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_empty_string(self):
        """Returns 400 response"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        publickey = ''
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_not_rsa_format(self):
        """Returns 400 response"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        publickey = 'abc'
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_public_key_bits_exceeds_maximum(self):
        """Returns 400 response"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        # over 16384 bits
        publickey = 'ssh-rsa ' + 'A' * 2048 + ' openstack@ubuntu'
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_exists(self):
        """Returns 202 response"""
        # create a keypair for test
        keyname = 'key_' + self._testMethodName
        self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.delete_keypair(keyname)
        self.assertEqual('202', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_is_used_by_server(self):
        """Returns 409 response"""
        # create a keypair for test
        keyname = 'key_' + self._testMethodName
        self.kp_client.create_keypair(keyname)

        # create a server for test
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
                                                    key_name=keyname)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # execute and assert
        resp, body = self.kp_client.delete_keypair(keyname)
        self.assertEqual('409', resp['status'])

        # cleanup a server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_does_not_exist(self):
        """Returns 404 response"""
        # execute and assert
        keyname = 'key_' + self._testMethodName
        resp, body = self.kp_client.delete_keypair('')
        self.assertEqual('404', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    def test_delete_keypair_when_user_does_not_have_admin_role(self):
        # create a keypair for test
        keyname = 'key_' + self._testMethodName
        self.kp_client_for_user1.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client_for_user1.delete_keypair(keyname)
        self.assertEqual('202', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    @test.skip_test('Skip this case.')
    @attr(kind='medium')
    def test_delete_keypair_when_keypair_name_is_double_byte_code(self):
        """Returns 404 response"""
        # execute and assert
        resp, body = self.kp_client.delete_keypair('\xef\xbb\xbf')
        print "resp=", resp
        self.assertEqual('404', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -h%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)