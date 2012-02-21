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
from nova import test

from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name
from storm import exceptions

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = storm.config.StormConfig('etc/large.conf')
test_config = storm.config.StormConfig('etc/large_test.conf')
config = default_config
environ_processes = []


def setUpModule(module):
#    environ_processes = module.environ_processes
    config = module.config


class FunctionalTest(unittest.TestCase):

    config = default_config
    config2 = test_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.os2 = openstack.Manager(config=self.config2)
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
                    resp, _ = self.os.servers_client.delete_server(s['id'])
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

    def exec_sql(self, sql, db='nova'):
        exec_sql = 'mysql -u %s -p%s -h%s ' + db + ' -e "' + sql + '"'
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password,
                              self.config.mysql.host),
                              shell=True)

    def get_data_from_mysql(self, sql, db='nova'):
        exec_sql = 'mysql -u %s -p%s -h%s ' + db + ' -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.user,
                                         self.config.mysql.password,
                                         self.config.mysql.host),
                                         shell=True)

        return result


class CreateServerTest(FunctionalTest):
    def setUp(self):
        super(CreateServerTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    @attr(kind='large')
    def test_create_server_when_snapshot_is_during_saving_process(self):
        print """

        test_create_server_when_snapshot_is_during_saving_process

        """

        print """

        creating server.

        """
        meta = {'aaa': 'bbb'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

        self.assertEquals('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = self._testMethodName + '_snapshot'
        resp, body = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('202', resp['status'])

        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(
                                            name + '_from_created_image',
                                            alt_img_id,
                                            self.flavor_ref,
                                            meta=meta,
                                            accessIPv4=accessIPv4,
                                            accessIPv6=accessIPv6,
                                            personality=personality)
        self.assertEquals('400', resp['status'])

    @attr(kind='large')
    def test_create_server_any_name(self):
        print """

        test_create_server_any_name

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

    @attr(kind='large')
    def test_create_server_name_is_num(self):
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_server_name_is_empty(self):
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_server_names_length_over_256(self):
        print """

        test_create_server_names_length_over_256

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'a' * 256
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

    @attr(kind='large')
    def test_create_server_with_the_same_name(self):
        print """

        test_create_server_with_the_same_name

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

    @attr(kind='large')
    def test_create_server_specify_illegal_characters(self):
        print """

        test_create_server_specify_illegal_characters

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = "illegal_char_/.\@:_name"
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
        print "body=", server
        self.assertEqual('200', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        self.assertEqual('200', resp['status'])
        self.assertEqual(name, server['name'])

    @attr(kind='large')
    def test_create_server_specify_double_byte(self):
        print """

        test_create_server_specify_double_byte

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = '\xef\xbb\xbf'
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
        print "body=", server
        self.assertEqual('500', resp['status'])


    @attr(kind='large')
    def test_create_server_specify_exists_image(self):
        print """

        test_create_server_specify_exists_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

        self.assertEqual('202', resp['status'])
        print "resp=", resp
        print "server=", server

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])
        self.assertEqual(str(self.image_ref), server['image']['id'])

    @attr(kind='large')
    def test_create_servers_specify_not_exists_image(self):
        print """

        test_create_servers_specify_not_exists_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        image_ref = sys.maxint
        resp, body = self.ss_client.create_server(name,
                                                  image_ref,
                                                  self.flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_not_specify_image(self):
        print """

        test_list_servers_not_specify_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_invalid_fixed_ip_address(self):
        print """

        test_create_servers_specify_invalid_fixed_ip_address
        """

        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_invalid_uuid(self):
        print """

        test_create_servers_specify_invalid_uuid

        """

        meta = {'hello': 'world'}
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_server_specify_exists_flavor(self):
        print """

        test_create_server_specify_exists_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

    @attr(kind='large')
    def test_create_servers_specify_not_exists_flavor(self):
        print """

        test_create_servers_specify_not_exists_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        flavor_ref = sys.maxint
        resp, body = self.ss_client.create_server(name,
                                                  self.image_ref,
                                                  flavor_ref,
                                                  meta=meta,
                                                  accessIPv4=accessIPv4,
                                                  accessIPv6=accessIPv6,
                                                  personality=personality)

        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_not_specify_flavor(self):
        print """

        test_create_servers_not_specify_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_not_exists_networks(self):
        print """

        test_create_servers_specify_not_exists_networks

        """
        uuid = '12345678-90ab-cdef-fedc-ba0987654321'
        sql = "select uuid from networks where uuid = '" + uuid + "';"
        rs = self.get_data_from_mysql(sql)
        self.assertEqual(0, len(rs))

        meta = {'hello': 'world'}
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_keypair(self):
        print """

        test_create_servers_specify_keypair

        """

        # create keypair
        keyname = rand_name('key')
        resp, keypair = self.kp_client.create_keypair(keyname)
        resp, body = self.os.keypairs_client.list_keypairs()

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server_kw(
                                                name=name,
                                                imageRef=self.image_ref,
                                                flavorRef=self.flavor_ref,
                                                metadata=meta,
                                                key_name=keyname,
                                                personality=personality)
        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        resp, body = self.ss_client.get_server(server['id'])
        print "body=", body
        self.assertEqual(keyname, body['key_name'])

    @attr(kind='large')
    def test_create_servers_specify_not_exists_keypair(self):
        print """

        test_create_servers_specify_not_exists_keypair

        """

        # create keypair
        keyname = rand_name('key')
        meta = {'hello': 'world'}
        name = self._testMethodName
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
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.649')
    @attr(kind='large')
    def test_create_server_specify_other_tenant_image(self):
        print """

        test_create_server_specify_other_tenant_image

        """

        # create server => tenant:admin
        name = self._testMethodName + '_admin'
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
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

        # snapshot => tenant:admin
        alt_name = self._testMethodName + '_snapshot'
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        # create server => tenant:demo
        demo_name = self._testMethodName + '_demo'
        resp, server = self.s2_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        print "resp=", resp
        print "body=", server
        self.assertEqual('403', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_networks(self):
        print """

        test_create_servers_specify_networks

        """

        sql = 'select uuid from networks where cidr=\'10.0.0.0/24\' limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.0.9',
                     'uuid':uuid}]
        resp, server = self.ss_client.create_server_kw(
                                                name=name,
                                                imageRef=self.image_ref,
                                                flavorRef=self.flavor_ref,
                                                metadata=meta,
                                                networks=networks,
                                                personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_two_networks(self):
        print """

        test_create_servers_specify_two_networks
        """

        sql = 'select uuid from networks where project_id = 1 limit 2;'
        uuids = self.get_data_from_mysql(sql)
        uuid = []
        for id in uuids.split('\n'):
            print "id=", id
            if id:
                uuid.append(id)

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.0.100', 'uuid': uuid[0]},
                    {'fixed_ip': '10.0.1.100', 'uuid': uuid[1]}]
        resp, server = self.ss_client.create_server_kw(
                                                   name=name,
                                                   imageRef=self.image_ref,
                                                   flavorRef=self.flavor_ref,
                                                   metadata=meta,
                                                   networks=networks,
                                                   personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual('200', resp['status'])

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_create_servers_specify_already_used_uuid(self):
        print """

        test_create_servers_specify_already_used_uuid

        """
        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = self._testMethodName + '1'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.0.1',
                     'uuid':uuid}]
        resp, server = self.ss_client.create_server_kw(
                                                name=name,
                                                imageRef=self.image_ref,
                                                flavorRef=self.flavor_ref,
                                                metadata=meta,
                                                networks=networks,
                                                personality=personality)

        self.assertEqual('202', resp['status'])
        print "resp1=", resp
        print "body1=", server

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        meta = {'hello': 'world'}
        name = self._testMethodName + '2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.0.1',
                     'uuid':uuid}]
        resp, server = self.ss_client.create_server_kw(
                                                name=name,
                                                imageRef=self.image_ref,
                                                flavorRef=self.flavor_ref,
                                                metadata=meta,
                                                networks=networks,
                                                personality=personality)

        self.assertEqual('400', resp['status'])
        print "resp2=", resp
        print "body2=", server

    @test.skip_test('ignore this case for bug.651')
    @attr(kind='large')
    def test_create_servers_specify_not_exists_ip_in_networks(self):
        print """

        test_create_servers_specify_not_exists_ip_in_networks(Bug.651)

        """

        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '192.168.0.1',
                     'uuid':uuid}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     networks=networks,
                                                     personality=personality)

        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_not_exists_zone(self):
        print """

        test_create_servers_specify_not_exists_zone

        """

        zone = rand_name('zone:')

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     availability_zone=zone,
                                                     personality=personality)
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_illegal_host(self):
        print """

        test_create_servers_specify_illegal_host

        """

        zone = 'nova:'

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(name=name,
                                                     imageRef=self.image_ref,
                                                     flavorRef=self.flavor_ref,
                                                     metadata=meta,
                                                     availability_zone=zone,
                                                     personality=personality)
        print "resp=", resp
        print "body=", body
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          body['id'],
                          'ACTIVE')
#        self.assertEqual('400', resp['status'])

    @attr(kind='large')
    def test_create_servers_specify_exists_zone(self):
        print """

        test_create_servers_specify_exists_zone

        """

        sql = ("select availability_zone, host from services "
               "where services.binary = 'nova-compute';")
        zone, host = (self.get_data_from_mysql(sql))[:-1].split('\t')
        availability_zone = zone + ':' + host

        meta = {'hello': 'world'}
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, body = self.ss_client.create_server_kw(
                                         name=name,
                                         imageRef=self.image_ref,
                                         flavorRef=self.flavor_ref,
                                         metadata=meta,
                                         availability_zone=availability_zone,
                                         personality=personality)
        print "resp=", resp
        print "body=", body
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(body['id'], 'ACTIVE')
        resp, body = self.ss_client.get_server(body['id'])
        print "body=", body
        self.assertEqual('200', resp['status'])

    @attr(kind='large')
    def test_ceate_server_specify_overlimit_to_meta(self):
        print """

        test_ceate_server_specify_overlimit_to_meta

        """

        print """

        creating server.

        """
        meta = {'a': 'b' * 260}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
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

    @attr(kind='large')
    def test_create_server_quota_cpu(self):
        print """

        test_create_server_quota_cpu

        """

        sql = ('INSERT INTO quotas(deleted, project_id, resource, hard_limit)'
               "VALUES(0, '1', 'cores', 2)")
        self.exec_sql(sql)

        print """

        creating server.

        """
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name + '1',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, server = self.ss_client.create_server(name + '2',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, server = self.ss_client.create_server(name + '3',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('413', resp['status'])

        sql = "delete from quotas;"
        self.exec_sql(sql)

    @test.skip_test('ignore this case for bug.619')
    @attr(kind='large')
    def test_create_server_quota_memory(self):
        print """

        test_create_server_quota_memory(#619)

        """

        sql = ('INSERT INTO quotas(deleted, project_id, resource, hard_limit)'
               "VALUES(0, '3', 'ram', 1024)")
        self.exec_sql(sql)

        print """

        creating server.

        """
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.s2_client.create_server(name + '1',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, server = self.s2_client.create_server(name + '2',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, server = self.s2_client.create_server(name + '3',
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('413', resp['status'])

        sql = "delete from quotas;"
        self.exec_sql(sql)

    @test.skip_test('ignore this case for bug.619')
    @attr(kind='large')
    def test_create_server_quota_disk(self):
        print """

        test_create_server_quota_disk(Bug.619)

        """

        sql = ('INSERT INTO quotas(deleted, project_id, resource, hard_limit)'
               "VALUES(0, 'admin', 'gigabyte', 1)")
        self.exec_sql(sql)

        print """

        creating server.

        """
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    2,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('413', resp['status'])