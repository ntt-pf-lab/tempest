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

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = storm.config.StormConfig('etc/medium.conf')
test_config = storm.config.StormConfig('etc/medium_test.conf')
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
        exec_sql = 'mysql -u %s -p%s ' + db + ' -e "' + sql + '"'
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                              shell=True)

    def get_data_from_mysql(self, sql, db='nova'):
        exec_sql = 'mysql -u %s -p%s ' + db + ' -Ns -e "' + sql + '"'
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
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    def update_status(self, server_id, vm_state, task_state, deleted=0):
        sql = ("UPDATE instances SET "
               "deleted = %s, "
               "vm_state = '%s', "
               "task_state = '%s' "
               "WHERE id = %s;") % (deleted, vm_state, task_state, server_id)
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_servers_when_no_server_created(self):
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
        print """

        test_list_servers_when_one_server_created

        """
        print """

        creating server.

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

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_when_three_servers_created(self):
        print """

        test_list_servers_when_three_servers_created

        """

        print """

        creating servers(three servers).

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name + str(i),
                                                self.image_ref,
                                                self.flavor_ref,
                                                meta=meta,
                                                accessIPv4=accessIPv4,
                                                accessIPv6=accessIPv6,
                                                personality=personality)

            print "%r %r" % (resp, server)
            # Wait for the server to become active
            self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_status_is_deleted(self):
        print """

        test_list_servers_status_is_deleted

        """

        print """

        creating server.

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

        print """

        delete server.

        """
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_detail_when_no_server_created(self):
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
        print """

        test_list_servers_detail_when_one_server_created

        """

        print """

        creating server.

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

        print """

        list servers with detail.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))
        self.assertEqual('ACTIVE', body['servers'][0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_when_three_servers_created(self):
        print """

        test_list_servers_detail_when_three_servers_created

        """

        print """

        creating servers(three servers).

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name + str(i),
                                                self.image_ref,
                                                self.flavor_ref,
                                                meta=meta,
                                                accessIPv4=accessIPv4,
                                                accessIPv6=accessIPv6,
                                                personality=personality)

            # Wait for the server to become active
            self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        print """

        list servers with detail.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(body['servers']))
        for i in range(0, 3):
            self.assertEqual('ACTIVE', body['servers'][i]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_building(self):
        print """

        test_list_servers_detail_status_is_building

        """

        print """

        creating server.

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

        print """

        list servers with detail. no wait for server status is active.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('BUILD', body['servers'][0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_active(self):
        print """

        test_list_servers_detail_status_is_active

        """

        print """

        creating server.

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

        print """

        list servers with detail. wait for server status is active.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('ACTIVE', body['servers'][0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_after_delete_server(self):
        print """

        test_list_servers_detail_after_delete_server

        """

        print """

        creating server.

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

        print """

        delete server.

        """
        self.ss_client.delete_server(server['id'])
        print "delete:resp=", resp

        print """

        list servers with detail. not wait for server's status is deleted.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual('ACTIVE', body['servers'][0]['status'])

        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_deleted(self):
        print """

        test_list_servers_detail_after_delete_server

        """

        print """

        creating server.

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

        print """

        delete server.

        """
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        print """

        list servers with detail. wait for server's status is deleted.

        """
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

        print """

        creating server.

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

        print """

        make snapshot of instance.

        """
        alt_name = self._testMethodName + '_snapshot'
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        #creating server from snapshot.
        print """

        creating server from created image.

        """
        resp, server = self.ss_client.create_server(
                                            name + '_from_created_image',
                                            alt_img_id,
                                            self.flavor_ref,
                                            meta=meta,
                                            accessIPv4=accessIPv4,
                                            accessIPv6=accessIPv6,
                                            personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        print """

        list servers.

        """
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

        print """

        creating server.

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

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers({'image': sys.maxint})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_string_to_image(self):
        print """

        test_list_servers_specify_string_to_image

        """

        print """

        creating server.

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

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers({'image': 'image'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_image(self):
        print """

        test_list_servers_specify_overlimits_to_image

        """

        print """

        creating server.

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

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers({'image': sys.maxint + 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_negative_to_image(self):
        print """

        test_list_servers_specify_negative_to_image

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

        resp, body = self.ss_client.list_servers({'image': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_flavor(self):
        print """

        test_list_servers_specify_exists_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': self.flavor_ref})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_not_exists_flavor(self):
        print """

        test_list_servers_specify_not_exists_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': sys.maxint})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_string_to_flavor(self):
        print """

        test_list_servers_specify_string_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': 'flavor'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_flavor(self):
        print """

        test_list_servers_specify_overlimits_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': sys.maxint + 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_negative_to_flavor(self):
        print """

        test_list_servers_specify_negative_to_flavor

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

        resp, body = self.ss_client.list_servers({'flavor': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_server_name(self):
        print """

        test_list_servers_specify_exists_server_name

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        name2 = self._testMethodName + '2'
        resp, server = self.ss_client.create_server(name2,
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

        resp, body = self.ss_client.list_servers({'name': 'servername'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @test.skip_test('ignore this case for bug.606')
    @attr(kind='medium')
    def test_list_servers_specify_empty_to_server_name(self):
        print """

        test_list_servers_specify_empty_to_server_name

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

        resp, body = self.ss_client.list_servers({'name': ''})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_server_name(self):
        print """

        test_list_servers_specify_overlimits_to_server_name

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

        resp, body = self.ss_client.list_servers({'name': 'a' * 256})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_num_to_server_name(self):
        print """

        test_list_servers_specify_num_to_server_name

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

        resp, body = self.ss_client.list_servers({'name': 99})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_status_active(self):
        print """

        test_list_servers_specify_status_active

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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
        server_id = server['id']

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))
        self.assertEqual(server_id, body['servers'][0]['id'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

    @attr(kind='medium')
    def test_list_servers_specify_status_build_when_server_is_build(self):
        print """

        test_list_servers_specify_status_build_when_server_is_build

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'status': 'BUILD'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))
        self.assertEqual(server['id'], body['servers'][0]['id'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

    @attr(kind='medium')
    def test_list_servers_specify_status_build_when_server_is_active(self):
        print """

        test_list_servers_specify_status_build_when_server_is_active

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

        resp, body = self.ss_client.list_servers({'status': 'BUILD'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

    @attr(kind='medium')
    def test_list_servers_specify_status_is_invalid(self):
        print """

        test_list_servers_specify_status_is_invalid

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

        resp, body = self.ss_client.list_servers({'status': 'DEAD'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_num_to_status(self):
        print """

        test_list_servers_specify_num_to_status

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

        resp, body = self.ss_client.list_servers({'status': 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_limits(self):
        print """

        test_list_servers_specify_limits

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'limit': 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_specify_limits_over_servers(self):
        print """

        test_list_servers_specify_limits_over_servers

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'limit': 3})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_string_to_limits(self):
        print """

        test_list_servers_specify_string_to_limits

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'limit': 'limit'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_limits(self):
        print """

        test_list_servers_specify_negative_to_limits

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'limit': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_limits(self):
        print """

        test_list_servers_specify_overlimits_to_limits

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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

        resp, body = self.ss_client.list_servers({'limit': sys.maxint + 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @test.skip_test('ignore this case')
    @attr(kind='medium')
    def test_list_servers_specify_change_since(self):
        print """

        test_list_servers_specify_change_since(Bug605)

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName + '1'
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

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName + '2'
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
        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, body = self.ss_client.list_servers(
                                    {'changes-since': '2011-01-01T12:34Z'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(2, len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_specify_invalid_change_since(self):
        print """

        test_list_servers_specify_invalid_change_since

        """
        resp, body = self.ss_client.list_servers(
                                    {'changes-since': '2011/01/01'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_future_date_to_change_since(self):
        print """

        test_list_servers_specify_future_date_to_change_since

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

        resp, body = self.ss_client.list_servers(
                                    {'changes-since': '2999-12-31T12:34Z'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_server_specify_other_tenant_server(self):
        print """

        test_list_server_specify_other_tenant_server

        """

        # server1 => tenant:demo
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]

        name_demo = self._testMethodName_demo
        resp, server = self.s2_client.create_server(name_demo,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp:demo=", resp
        print "server:demo=", server
        # Wait for the server to become active
        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')

        # server2 => tenant:admin
        name_admin = self._testMethodName & '_admin'
        resp, server = self.ss_client.create_server(name_admin,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.s2_client.list_servers({'name': name_admin})
        print "resp=", resp
        print "body=", body
        self.assertEqual('401', resp['status'])

    @attr(kind='medium')
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

    @attr(kind='medium')
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

    @attr(kind='medium')
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

    @attr(kind='medium')
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

    @attr(kind='medium')
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

    @attr(kind='medium')
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


