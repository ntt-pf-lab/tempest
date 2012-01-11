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
from storm import openstack, exceptions
import storm.config
from storm.common.utils.data_utils import rand_name


"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

# for admin tenant
default_config = storm.config.StormConfig('etc/medium.conf')
# for demo tenant
test_config = storm.config.StormConfig('etc/medium_test.conf')
config = default_config
environ_processes = []


def setUpModule(module):
    config = module.config


class FunctionalTest(unittest.TestCase):

    config = default_config
    config2 = test_config

    def setUp(self):
        # for admin tenant
        self.os = openstack.Manager(config=self.config)
        # for demo tenant
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
                    print "Find existing instance %s" % s
                    resp, _ = self.os.servers_client.delete_server(s['id'])
                    print "Delete Server Response %s" % resp
                    if resp['status'] == '204' or resp['status'] == '202':
                        print "Wait for stop %s" % s['id']
                        self.os.servers_client.wait_for_server_not_exists(
                                                                    s['id'])
                except Exception as e:
                    print e
        except Exception:
            pass
        print """

        Cleanup DB

        """

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


class ServersActionTest(FunctionalTest):
    def setUp(self):
        super(ServersActionTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        # for admin tenant
        self.ss_client = self.os.servers_client
        # for demo tenant
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client

    def create_dummy_instance(self, vm_state, task_state, deleted=0):

        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = rand_name('dummy')
        file_contents = 'This is a test_file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        sql = ("UPDATE instances SET "
               "deleted = %s, "
               "vm_state = '%s', "
               "task_state = '%s' "
               "WHERE id = %s;") % (
                            deleted, vm_state, task_state, server['id'])
        self.exec_sql(sql)

        return server['id']

    @attr(kind='medium')
    def _test_reboot_403_base(self, vm_state, task_state, deleted=0):
        server_id = self.create_dummy_instance(vm_state, task_state, deleted)
        resp, _ = self.ss_client.reboot(server_id, 'HARD')
        self.assertEquals('403', resp['status'])
        sql = ("UPDATE instances SET "
               "vm_state = 'active',"
               "task_state = null "
               "WHERE id = %s;") % server_id
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_reboot_when_vm_eq_building_and_task_eq_scheduling(self):
        self._test_reboot_403_base("building", "scheduling")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_building_and_task_eq_networking(self):
        self._test_reboot_403_base("building", "networking")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_building_and_task_eq_bdm(self):
        self._test_reboot_403_base("building", "block_device_mapping")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_building_and_task_eq_spawning(self):
        self._test_reboot_403_base("building", "spawning")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_active_and_task_eq_image_snapshot(self):
        self._test_reboot_403_base("active", "image_snaphost")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_active_and_task_eq_image_backup(self):
        self._test_reboot_403_base("active", "image_backup")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_active_and_task_eq_updating_password(self):
        self._test_reboot_403_base("active", "updating_password")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_active_and_task_eq_rebuilding(self):
        self._test_reboot_403_base("active", "rebuilding")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_building_and_task_eq_deleting(self):
        self._test_reboot_403_base("building", "deleting")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_active_and_task_eq_deleting(self):
        self._test_reboot_403_base("active", "deleting")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_error_and_task_eq_building(self):
        self._test_reboot_403_base("error", "building")

    @attr(kind='medium')
    def test_reboot_when_vm_eq_error_and_task_eq_error(self):
        self._test_reboot_403_base("error", "error")

    @attr(kind='medium')
    def test_reboot_when_specify_not_exist_server_id(self):
        print """

        reboot server

         """
        test_id = sys.maxint
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        print "resp= ", resp
        print "server= ", server
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_specify_uuid_as_id(self):

        print """

        creating server.

        """
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = self._testMethodName
        file_contents = 'This is a test_file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        test_id = server['uuid']
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('2.2.2.2', server['accessIPv4'])
        self.assertEqual('::babe:330.23.33.3', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

    @test.skip_test('Skip this case for bug #636')
    @attr(kind='medium')
    def test_reboot_when_specify_server_of_another_tenant(self):

        resp, body = self.ss_client.list_servers()
        print "resp1-1(empty)=", resp
        print "body1-1(empty)=", body

        print """

        creating server of demo(not admin).

        """

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.2'
        accessIPv6 = '::babe:220.12.22.3'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.s2_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_server_id2 = server['id']
        resp, server = self.ss_client.get_server(test_server_id2)
        self.assertEquals('200', resp['status'])

        print """

        creating server of admin(is admin).

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

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_server_id = server['id']
        resp, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('200', resp['status'])

        print """

        rebooting other tenant's server.

        """

        resp, server = self.s2_client.reboot(test_server_id, 'HARD')
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_specify_string_as_id(self):

        print """

        reboot server

         """
        invalid_test_id = 'opst_test'
        resp, _ = self.ss_client.reboot(invalid_test_id, 'HARD')
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_specify_negative_number_as_id(self):

        print """

        reboot server

         """

        reboot_id = -1
        resp, _ = self.ss_client.reboot(reboot_id, 'HARD')
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_id_is_over_max_int(self):

        print """

        reboot server

         """

        reboot_id = 2147483648
        resp, _ = self.ss_client.reboot(reboot_id, 'HARD')
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_running(self):

        print """

        creating server.

        """
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = self._testMethodName
        file_contents = 'This is a test_file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('2.2.2.2', server['accessIPv4'])
        self.assertEqual('::babe:330.23.33.3', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

    @test.skip_test('Skip this case for bug #476')
    @attr(kind='medium')
    def test_reboot_when_server_is_during_reboot_process(self):

        print """

        creating server.

        """
        meta = {'open': 'stack'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        print """

        reboot server

         """
        resp1, _ = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('202', resp1['status'])

        print """

        reboot server without waiting done creating

         """
        resp2, server2 = self.ss_client.reboot(test_id, 'HARD')
        print "resp2=", resp2
        print "server2=", server2
        self.assertEquals('403', resp2['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_down(self):
        print """

        creating server.

        """
        meta = {'open': 'stack'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        test_id = server['id']
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')
        _, server = self.ss_client.get_server(test_id)
        self.assertEquals('ACTIVE', server['status'])

        print """

        deleting server

         """
        # Stop server
        self.ss_client.delete_server(test_id)
        self.ss_client.wait_for_server_not_exists(test_id)
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('404', resp['status'])

        print """

        reboot server

         """

        # Reboot stopped server
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('404', resp['status'])

    @test.skip_test('Skip this case for bug validation')
    @attr(kind='medium')
    def test_create_image(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_id = server['id']
        _, _ = self.ss_client.create_image(test_id, alt_name)
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, _ = self.ss_client.list_servers_with_detail()

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('ACTIVE', server['status'])

    @test.skip_test('ignore this case')
    @attr(kind='medium')
    def test_create_image_fat_snapshot(self):

        print """

        creating server.

        """
        SMALL_FLAVOR_REF = '2'  # ref to m1.small
        LARGE_FLAVOR_REF = '4'  # ref to m1.large

        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    LARGE_FLAVOR_REF,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_id = server['id']
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        resp, body = self.ss_client.create_image(test_id, alt_name)
        print "respresp=", resp
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, body = self.ss_client.list_servers_with_detail()

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    SMALL_FLAVOR_REF,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    @test.skip_test('ignore this case')
    @attr(kind='medium')
    def test_create_image_when_specify_server_by_uuid(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_uuid = server['uuid']
        resp, _ = self.ss_client.create_image(test_uuid, alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, _ = self.img_client.get_image(alt_img_id)
        self.assertEquals('200', resp['status'])

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        uuid_ss_server_id = server['id']
        self.ss_client.wait_for_server_status(uuid_ss_server_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(uuid_ss_server_id)
        self.assertEquals('ACTIVE', server['status'])

    @attr(kind='medium')
    def test_create_image_specify_not_exist_server_id(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        resp, _ = self.ss_client.create_image(sys.maxint, 'opst_test')
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_specify_server_of_another_tenant(self):

        print """

        creating server of admin(is admin).

        """

        meta = {'aaa': 'bbb'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_server_id = server['id']
        resp, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('200', resp['status'])

        print """

        creating snapshot of admin's instance by not admin.

        """

        # Make snapshot of the instance.
        alt_name = rand_name('ss_test')
        resp, _ = self.s2_client.create_image(test_server_id, alt_name)
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_during_boot_process(self):

        print """

        creating server.

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.2.3.4'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        test_id = server['id']

        print """

        creating snapshot without waiting done creating server.

        """
        # Make snapshot without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('403', resp['status'])

    @test.skip_test('Skip this case for bug #476')
    @attr(kind='medium')
    def test_create_image_when_server_is_during_reboot_process(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        print """

        reboot server

         """
        _, server = self.ss_client.reboot(test_id, 'HARD')

        print """

        creating snapshot without waiting done rebooting server.

        """
        alt_name = rand_name('opst')
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        print "resp=", resp
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_during_stop_process(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_server_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        deleting server.

        """
        self.ss_client.delete_server(test_server_id)

        print """

        creating snapshot without waiting done stopping

         """
        # Make snapshot of the instance without waiting done creating server
        alt_name = rand_name('opst_test')
        resp, _ = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_down(self):

        print """

        creating server.

        """
        meta = {'opst': 'testing'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        deleting server.

        """
        self.ss_client.delete_server(test_server_id)
        self.ss_client.wait_for_server_not_exists(test_server_id)
        _, servers = self.ss_client.list_servers()
        self.assertEquals([], servers['servers'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals('404', resp['status'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_name)
        self.img_client.wait_for_image_not_exists(alt_name)

    @test.skip_test('Skip this case for bug #678')
    @attr(kind='medium')
    def test_create_image_when_other_image_is_during_saving_process(self):

        print """

        creating server.

        """
        meta = {'aaaaa': 'bbbbb'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('ACTIVE', server['status'])

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp1, _ = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals('202', resp1['status'])

        print """

        creating snapshot again during the other one is
                                                during process of image saving.

        """
        # Make snapshot of the instance.
        alt_test_name = rand_name('server_2')
        resp2, _ = self.ss_client.create_image(test_server_id,
                                                   alt_test_name)
        self.assertEquals('409', resp2['status'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        alt_img_url = resp1['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)

    @attr(kind='medium')
    def test_create_image_when_specify_duplicate_image_name(self):
        print """

        creating server.

        """
        meta = {'aaaaa': 'bbbbb'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('ACTIVE', server['status'])

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_server_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        
        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp1, _ = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals("202", resp1['status'])

        alt_img_url = resp1['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        # if task_state became none, can accept next api.
        db_result = 'server_state'
        while db_result != 'NULL':
            sql = ("SELECT task_state FROM instances WHERE id = %s;") % (test_server_id)
            db_result = (self.get_data_from_mysql(sql))[:-1]
            if db_result == 'NULL':
                break

        print """

        creating snapshot again.

        """
        # Make snapshot of the instance.
        alt_test_name = rand_name('server')
        resp2, _ = self.ss_client.create_image(test_server_id,
                                                   alt_test_name)
        self.assertEquals("202", resp2['status'])

        alt_test_img_url = resp2['location']
        match = re.search('/images/(?P<image_id>.+)', alt_test_img_url)
        self.assertIsNotNone(match)
        alt_test_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_test_img_id, 'ACTIVE')
        _, images = self.img_client.get_image(alt_test_img_id)
        self.assertEquals('ACTIVE', images['status'])

        print """

        creating server from snapshot.

        """
        _, server = self.ss_client.create_server(name,
                                                    alt_test_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        ss_server_id = server['id']
        self.ss_client.wait_for_server_status(ss_server_id, 'ACTIVE')
        _, server = self.ss_client.get_server(ss_server_id)
        self.assertEquals('ACTIVE', server['status'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_test_img_id)
        self.img_client.wait_for_image_not_exists(alt_test_img_id)
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)

    @attr(kind='medium')
    def test_create_image_when_specify_length_over_256_name(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('a' * 260)
        resp, body = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('400', resp['status'])
        print body

    @attr(kind='medium')
    def test_create_image_when_metadata_exists(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """

        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_id = server['id']
        meta = {'ImageType': 'Gold', 'ImageVersion': '2.0'}
        resp, _ = self.ss_client.create_image(test_id, alt_name, meta)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp_wait, _ = self.img_client.get_image(alt_img_id)
        self.assertEquals('200', resp_wait['status'])

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        ss_server_id = server['id']
        self.ss_client.wait_for_server_status(ss_server_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(ss_server_id)
        self.assertEquals('ACTIVE', server['status'])

    @test.skip_test('Skip this case for bug #642')
    @attr(kind='medium')
    def test_create_image_when_key_and_value_are_blank(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """

        # Make snapshot of the instance.
        test_id = server['id']
        alt_name = rand_name('server')
        meta = {'': ''}
        resp, _ = self.img_client.create_image(test_id,
                                                  alt_name,
                                                  meta=meta)
        self.assertEquals('400', resp['status'])
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp_wait, _ = self.img_client.get_image(alt_img_id)
        self.assertEquals('200', resp_wait['status'])

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        ss_server_id = server['id']
        self.ss_client.wait_for_server_status(ss_server_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(ss_server_id)
        self.assertEquals('ACTIVE', server['status'])

    @test.skip_test('Skip this case for bug #642')
    @attr(kind='medium')
    def test_ceate_image_when_specify_length_over_256_key_and_value(self):

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
        _, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        _, server = self.ss_client.get_server(test_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """

        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_id = server['id']
        meta = {'a' * 260: 'b' * 260}
        resp, _ = self.ss_client.create_image(test_id, alt_name, meta=meta)
        self.assertEquals('400', resp['status'])
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp_wait, image_wait = self.img_client.get_image(alt_img_id)
        print "resp_wait=", resp_wait
        print "image_wait=", image_wait
        self.assertEquals('200', resp_wait['status'])

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        print "resp=", resp
        print "server=", server
        # Wait for the server to become active
        ss_server_id = server['id']
        self.ss_client.wait_for_server_status(ss_server_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(ss_server_id)
        self.assertEquals('ACTIVE', server['status'])

    @attr(kind='medium')
    def _test_create_image_403_base(self, vm_state, task_state, deleted=0):
        server_id = self.create_dummy_instance(vm_state, task_state, deleted)
        name = rand_name('server')
        resp, _ = self.ss_client.create_image(server_id, name)
        self.assertEquals('403', resp['status'])
        sql = ("UPDATE instances SET "
               "vm_state = 'active',"
               "task_state = null "
               "WHERE id = %s;") % server_id
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_create_image_when_vm_eq_building_and_task_eq_scheduling(self):
        self._test_create_image_403_base("building", "scheduling")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_building_and_task_eq_networking(self):
        self._test_create_image_403_base("building", "networking")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_building_and_task_eq_bdm(self):
        self._test_create_image_403_base("building", "block_device_mapping")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_building_and_task_eq_spawning(self):
        self._test_create_image_403_base("building", "spawning")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_active_and_task_eq_image_backup(self):
        self._test_create_image_403_base("active", "image_backup")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_actv_and_task_eq_updating_password(self):
        self._test_create_image_403_base("active", "updating_password")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_active_and_task_eq_rebuilding(self):
        self._test_create_image_403_base("active", "rebuilding")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_active_and_task_eq_rebooting(self):
        self._test_create_image_403_base("active", "rebooting")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_building_and_task_eq_deleting(self):
        self._test_create_image_403_base("building", "deleting")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_active_and_task_eq_deleting(self):
        self._test_create_image_403_base("active", "deleting")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_error_and_task_eq_building(self):
        self._test_create_image_403_base("error", "building")

    @attr(kind='medium')
    def test_create_image_when_vm_eq_error_and_task_eq_error(self):
        self._test_create_image_403_base("error", "error")


class CreateImageFatTest(FunctionalTest):
    def setUp(self):
        super(CreateImageFatTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

        self.small_flavor_ref = 998
        subprocess.check_call('/opt/stack/nova/bin/nova-manage flavor create '
            '--name=small --memory=1024 --cpu=1 --local_gb=1 '
            '--flavor=%d --swap=0' % self.small_flavor_ref, shell=True)

        self.fat_flavor_ref = 999
        subprocess.check_call('/opt/stack/nova/bin/nova-manage flavor create '
            '--name=fat --memory=1024 --cpu=1 --local_gb=2 '
            '--flavor=%d --swap=0' % self.fat_flavor_ref, shell=True)

        def flush_flavors():
            subprocess.call('/opt/stack/nova/bin/nova-manage flavor delete small --purge', shell=True)
            subprocess.call('/opt/stack/nova/bin/nova-manage flavor delete fat --purge', shell=True)

        self.addCleanup(flush_flavors)

    @attr(kind='medium')
    def test_create_image_fat_snapshot(self):

        print """

        creating server.

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.fat_flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        test_id = server['id']
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        resp, body = self.ss_client.create_image(test_id, alt_name)
        print "respresp=", resp
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, body = self.ss_client.list_servers_with_detail()

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.small_flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')
