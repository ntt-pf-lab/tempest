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


class KeypairsTest(FunctionalTest):

    def setUp(self):
        super(KeypairsTest, self).setUp()
        self.kp_client = self.os.keypairs_client
        self.ss_client = self.os.servers_client

    @attr(kind='medium')
    def test_list_keypairs_when_keypair_amount_is_zero(self):
        """Returns 200 response with empty body"""
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
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
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        # create a keypair for test
        keyname = rand_name('key')
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
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_keypairs_when_keypair_amount_is_three(self):
        """Returns 200 response with a list of keypairs"""
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        # create three keypairs for test
        keynames = []
        for _ in range(0, 3):
            keyname = rand_name('key')
            self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.list_keypairs()
        self.assertEqual('200', resp['status'])
        keypairs = body['keypairs']
        self.assertEqual(3, len(keypairs))
        for keyname in keynames:
            self.assertTrue(keyname in [x['name'] for x in keypairs])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_is_specified(self):
        """Returns 200 response with an information of the created keypair"""
        # execute and assert
        keyname = rand_name('key')
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('200', resp['status'])
        keypair = body['keypair']
        self.assertTrue(keypair['fingerprint'])
        self.assertTrue(keypair['name'])
        self.assertTrue(keypair['private_key'])
        self.assertTrue(keypair['public_key'])
        self.assertTrue(keypair['user_id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_keypair_name_is_duplicated(self):
        """Returns 409 response"""
        # create a keypair for test
        keyname = rand_name('key')
        self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.create_keypair(keyname)
        self.assertEqual('409', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
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

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_specified(self):
        """Returns 200 response with information of the created keypair"""
        # execute and assert
        keyname = rand_name('key')
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
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_empty_string(self):
        """Returns 400 response"""
        # execute and assert
        keyname = rand_name('key')
        publickey = ''
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_public_key_is_not_rsa_format(self):
        """Returns 400 response"""
        # execute and assert
        keyname = rand_name('key')
        publickey = 'abc'
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_keypair_when_public_key_bits_exceeds_maximum(self):
        """Returns 400 response"""
        # execute and assert
        keyname = rand_name('key')
        # over 16384 bits
        publickey = 'ssh-rsa ' + 'A' * 2048 + ' openstack@ubuntu'
        resp, body = self.kp_client.create_keypair(keyname, publickey)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_exists(self):
        """Returns 202 response"""
        # create a keypair for test
        keyname = rand_name('key')
        self.kp_client.create_keypair(keyname)

        # execute and assert
        resp, body = self.kp_client.delete_keypair(keyname)
        self.assertEqual('202', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_is_used_by_server(self):
        """Returns 409 response"""
        # create a keypair for test
        keyname = rand_name('key')
        self.kp_client.create_keypair(keyname)

        # create a server for test
        name = rand_name('server')
        image_ref = self.config.env.image_ref
        flavor_ref = self.config.env.flavor_ref
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    image_ref,
                                                    flavor_ref,
                                                    meta=meta,
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
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_delete_keypair_when_keypair_does_not_exist(self):
        """Returns 404 response"""
        # execute and assert
        keyname = rand_name('key')
        resp, body = self.kp_client.delete_keypair('')
        self.assertEqual('404', resp['status'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D nova -e "'
                              'DELETE FROM key_pairs;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
