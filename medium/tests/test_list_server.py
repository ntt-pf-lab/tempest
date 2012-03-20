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
import sys

import unittest2 as unittest
from nose.plugins.attrib import attr
from nova import test

from tempest import openstack
import tempest.config


"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = tempest.config.TempestConfig('etc/medium.conf')
test_config = tempest.config.TempestConfig('etc/medium_test.conf')
config = default_config


def setUpModule(module):
    config = module.config

def tearDownModule(module):
    os = openstack.Manager(config=default_config)
    print """

    Terminate All Instances

    """
    try:
        _, servers = os.servers_client.list_servers()
        print "Servers : %s" % servers
        for s in servers['servers']:
            try:
                print "Find existing instance %s" % s['id']
                resp, _ = os.servers_client.delete_server(s['id'])
                print "Delete Server Response %s" % resp['status']
                if resp['status'] == '204' or resp['status'] == '202':
                    print "Wait for stop %d" % s['id']
                    os.servers_client.wait_for_server_not_exists(s['id'])
            except Exception as e:
                print e
    except Exception:
        pass

class FunctionalTest(unittest.TestCase):

    config = default_config
    config2 = test_config
    servers = []

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.os2 = openstack.Manager(config=self.config2)
        self.testing_processes = []

    def tearDown(self):
        print """

        Terminate Active Instances

        """
        try:
            for s in self.servers:
                try:
                    print "Find existing instance %s" % s
                    resp, _ = self.os.servers_client.delete_server(s)
                    print "Delete Server Response %s" % resp['status']
                    if resp['status'] == '204' or resp['status'] == '202':
                        print "Wait for stop %d" % s
                        self.os.servers_client.wait_for_server_not_exists(s)
                except Exception as e:
                    print e
        except Exception:
            pass
        print """

        Cleanup DB

        """
        self.servers[:] = []

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

    def get_instance(self, num_of_server):
        _, servers = self.ss_client.list_servers_with_detail()
        server = servers['servers']
        server = [s for s in server if s['status'] == 'ACTIVE']
        if server and len(server) >= num_of_server:
            return server[0:(num_of_server)]
        remain = num_of_server - len(server)
        for i in range(0,remain):
            server.append(self.create_instance(self._testMethodName + str(i)))
        return server

    def create_instance(self, server_name, image_id=None):
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = server_name
        file_contents = 'This is a test_file.'
        if not image_id:
            image_id = self.image_ref
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    image_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        return server


class ListServerTest(FunctionalTest):
    def setUp(self):
        super(ListServerTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_list_servers_when_no_server_created(self):
        print """

        test_list_servers_when_no_server_created

        """
        tearDownModule(None)
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        result = [s for s in body['servers'] if s['status'] == 'ACTIVE']
        self.assertEqual([], result)

    @attr(kind='medium')
    def test_list_servers_when_one_server_created(self):
        print """

        test_list_servers_when_one_server_created

        """
        print """

        creating server.

        """
        self.get_instance(1)

        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(0 < len(body['servers']))

    @attr(kind='medium')
    def test_list_servers_when_three_servers_created(self):
        print """

        test_list_servers_when_three_servers_created

        """

        print """

        creating servers(three servers).

        """
        servers = self.get_instance(3)
        print servers
        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(len(body['servers']) > 2)

    @attr(kind='medium')
    def test_list_servers_status_is_deleted(self):
        print """

        test_list_servers_status_is_deleted

        """

        print """

        creating server.

        """
        servers = self.get_instance(1)
        server = servers[0]
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
        servers = body['servers']
        result = [s for s in servers if s['id'] == server['id']]
        self.assertEqual('200', resp['status'])
        self.assertEqual([], result)

    @attr(kind='medium')
    def test_list_servers_detail_when_no_server_created(self):
        print """

        test_list_servers_detail_when_no_server_created

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        servers = body['servers']
        result = [s for s in servers if s['status'] == 'ACTIVE']
        self.assertEqual('200', resp['status'])
        self.assertEqual([], result)

    @attr(kind='medium')
    def test_list_servers_detail_when_one_server_created(self):
        print """

        test_list_servers_detail_when_one_server_created

        """

        print """

        creating server.

        """
        servers = self.get_instance(1)
        server = servers[0]
        print """

        list servers with detail.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        servers = body['servers']
        result = [s for s in servers if s['id'] == server['id']]
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(result))

    @attr(kind='medium')
    def test_list_servers_detail_when_three_servers_created(self):
        print """

        test_list_servers_detail_when_three_servers_created

        """

        print """

        creating servers(three servers).

        """
        servers = self.get_instance(3)
        print """

        list servers with detail.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        servers = body['servers']
        result = [s for s in servers if s['status'] == 'ACTIVE']
        self.assertEqual(3, len(result))

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
        self.servers.append(server['id'])

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
        servers = self.get_instance(1)
        print """

        list servers with detail. wait for server status is active.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        servers = body['servers']
        result = [s for s in servers if s['id'] == servers[0]['id']]
        self.assertEqual('ACTIVE', result[0]['status'])

    @attr(kind='medium')
    def test_list_servers_detail_after_delete_server(self):
        print """

        test_list_servers_detail_after_delete_server

        """

        print """

        creating server.

        """

        servers = self.get_instance(1)
        print """

        delete server.

        """
        self.ss_client.delete_server(servers[0]['id'])
        print """

        list servers with detail. not wait for server's status is deleted.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        servers = body['servers']
        result = [s for s in servers if s['id'] == servers[0]['id']]
        self.assertEqual('ACTIVE', result[0]['status'])

        self.ss_client.wait_for_server_not_exists(servers[0]['id'])

    @attr(kind='medium')
    def test_list_servers_detail_status_is_deleted(self):
        print """

        test_list_servers_detail_after_delete_server

        """

        print """

        creating server.

        """
        servers = self.get_instance(1)

        print """

        delete server.

        """
        self.ss_client.delete_server(servers[0]['id'])
        self.ss_client.wait_for_server_not_exists(servers[0]['id'])

        print """

        list servers with detail. wait for server's status is deleted.

        """
        resp, body = self.ss_client.list_servers_with_detail()
        print "resp=", resp
        print "body=", body
        servers = body['servers']
        result = [s for s in servers if s['id'] == servers[0]['id']]
        self.assertEqual('200', resp['status'])
        self.assertEqual([], result)

    @attr(kind='medium')
    def test_list_servers_specify_exists_image(self):
        print """

        test_list_servers_specify_exists_image

        """

        print """

        creating server.

        """
        servers = self.get_instance(1)
        print """

        make snapshot of instance.

        """
        alt_name = self._testMethodName + '_snapshot'
        resp, _ = self.ss_client.create_image(servers[0]['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        #creating server from snapshot.
        print """

        creating server from created image.

        """
        snap = self.create_instance(self._testMethodName, image_id=alt_img_id)
        self.servers.append(snap['id'])
        print """

        list servers.

        """
        resp, body = self.ss_client.list_servers({'image': self.image_ref})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(len(body['servers']) > 0)

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

        Not creating server.

        """
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
        resp, body = self.ss_client.list_servers({'image': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_flavor(self):
        print """

        test_list_servers_specify_exists_flavor

        """
        self.get_instance(1)
        resp, body = self.ss_client.list_servers({'flavor': self.flavor_ref})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(len(body['servers']) > 0)

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_flavor(self):
        print """

        test_list_servers_specify_not_exists_flavor

        """
        resp, body = self.ss_client.list_servers({'flavor': sys.maxint})
        print "resp=", resp
        print "body=", body
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_string_to_flavor(self):
        print """

        test_list_servers_specify_string_to_flavor

        """
        resp, body = self.ss_client.list_servers({'flavor': 'flavor'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('404', resp['status'])

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_flavor(self):
        print """

        test_list_servers_specify_overlimits_to_flavor

        """
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
        resp, body = self.ss_client.list_servers({'flavor': -1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_server_name(self):
        print """

        test_list_servers_specify_exists_server_name

        """

        server = self.get_instance(1)
        resp, body = self.ss_client.list_servers({'name': server[0]['name']})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual(server[0]['name'], body['servers'][0]['name'])

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_server_name(self):
        print """

        test_list_servers_specify_not_exists_server_name

        """
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
        resp, body = self.ss_client.list_servers({'name': 99})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_status_active(self):
        print """

        test_list_servers_specify_status_active

        """
        self.get_instance(1)

        resp, body = self.ss_client.list_servers({'status': 'ACTIVE'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(len(body['servers']) > 0)


    @attr(kind='medium')
    def test_list_servers_specify_status_build_when_server_is_build(self):
        print """

        test_list_servers_specify_status_build_when_server_is_build

        """
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
        self.servers.append(server['id'])

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
        self.get_instance(1)

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
        resp, body = self.ss_client.list_servers({'status': 'DEAD'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_num_to_status(self):
        print """

        test_list_servers_specify_num_to_status

        """
        resp, body = self.ss_client.list_servers({'status': 1})
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_limits(self):
        print """

        test_list_servers_specify_limits

        """
        self.get_instance(2)

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
        self.get_instance(2)
        resp, body = self.ss_client.list_servers({'limit': 100})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertTrue(len(body['servers']) < 100)

    @test.skip_test('ignore this case for bug.605')
    @attr(kind='medium')
    def test_list_servers_specify_string_to_limits(self):
        print """

        test_list_servers_specify_string_to_limits

        """
        resp, body = self.ss_client.list_servers({'limit': 'limit'})
        print "resp=", resp
        print "body=", body
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_limits(self):
        print """

        test_list_servers_specify_negative_to_limits

        """
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
        self.get_instance(2)

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
    def test_get_server_details_by_id(self):
        print """

        test_get_server_details_by_id

        """
        server = self.get_instance(1)[0]

        resp, body = self.ss_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(server['name'], body['name'])

    @attr(kind='medium')
    def test_get_server_details_by_uuid(self):
        print """

        test_get_server_details_by_uuid

        """
        server = self.get_instance(1)[0]
        resp, body = self.ss_client.get_server(server['id'])

        uuid = body['uuid']

        resp, body = self.ss_client.get_server(uuid)
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(server['id'], body['id'])

    @attr(kind='medium')
    def test_get_server_details_by_not_exists_id(self):
        print """

        test_get_server_details_by_not_exists_id

        """
        resp, body = self.ss_client.get_server(999999)  # not exists
        print "resp=", resp
        print "body=", body

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_other_tenant_server(self):
        print """

        test_get_server_details_specify_other_tenant_server

        """
        server = self.get_instance(1)[0]
        # get server => tenant:demo
        resp, body = self.s2_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body
        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_string_to_id(self):
        print """

        test_get_server_details_specify_string_to_id

        """
        resp, body = self.ss_client.get_server('abcdefghij')
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_negative_to_id(self):
        print """

        test_get_server_details_specify_negative_to_id

        """
        resp, body = self.ss_client.get_server(-1)
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_overlimits_to_id(self):
        print """

        test_get_server_details_specify_overlimits_to_id

        """
        resp, body = self.ss_client.get_server(sys.maxint + 1)
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])


class GetServerTest(FunctionalTest):
    def setUp(self):
        super(GetServerTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_get_server_details_by_id(self):
        print """

        test_get_server_details_by_id

        """
        server = self.get_instance(1)[0]
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(server['name'], body['name'])

    @attr(kind='medium')
    def test_get_server_details_by_uuid(self):
        print """

        test_get_server_details_by_uuid

        """
        server = self.get_instance(1)[0]

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
        print """

        test_get_server_details_by_not_exists_id

        """
        resp, body = self.ss_client.get_server(999999)  # not exists
        print "resp=", resp
        print "body=", body

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_other_tenant_server(self):
        print """

        test_get_server_details_specify_other_tenant_server

        """
        server = self.get_instance(1)[0]
        # get server => tenant:demo
        resp, body = self.s2_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body
        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_string_to_id(self):
        print """

        test_get_server_details_specify_string_to_id

        """
        resp, body = self.ss_client.get_server('abcdefghij')
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_negative_to_id(self):
        print """

        test_get_server_details_specify_negative_to_id

        """
        resp, body = self.ss_client.get_server(-1)
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_overlimits_to_id(self):
        print """

        test_get_server_details_specify_overlimits_to_id

        """
        resp, body = self.ss_client.get_server(sys.maxint + 1)
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])
