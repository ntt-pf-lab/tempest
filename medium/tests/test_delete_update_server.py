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
environ_processes = []


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

    def get_instance(self):
        _, servers = self.ss_client.list_servers_with_detail()
        server = servers['servers']
        server = [s for s in server if s['status'] == 'ACTIVE']
        if server:
            return server[0]
        return self.create_instance(self._testMethodName)

    def create_instance(self, server_name):
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = server_name
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
        return server

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


class DeleteServerTest(FunctionalTest):
    def setUp(self):
        super(DeleteServerTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    def update_status(self, server_id, vm_state, task_state, deleted=0):
        if task_state is not None:
            sql = ("UPDATE instances SET "
                   "deleted = %s, "
                   "vm_state = '%s', "
                   "task_state = '%s' "
                   "WHERE id = %s;") \
                   % (deleted, vm_state, task_state, server_id)
        else:
            sql = ("UPDATE instances SET "
                   "deleted = %s, "
                   "vm_state = '%s', "
                   "task_state = NULL "
                   "WHERE id = %s;") % (deleted, vm_state, server_id)
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_delete_server(self):
        print """

        test_delete_server

        """
        server = self.get_instance()
        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_not_exists_id(self):
        print """

        test_delete_server_not_exists_id

        """
        resp = self.ss_client.delete_server(999999)  # not exists
        print "resp=", resp
        self.assertEqual('404', resp[0]['status'])

    @attr(kind='medium')
    def test_delete_server_when_server_is_building(self):
        print """

        test_delete_server_when_server_is_building

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

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_when_server_is_deleted(self):
        print """

        test_delete_server_when_server_is_deleted

        """
        server = self.get_instance()

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_other_tenant_server(self):
        print """

        test_delete_server_specify_other_tenant_server

        """
        server = self.get_instance()

        # delete server => tenant:demo
        resp, _ = self.s2_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_string_to_server_id(self):
        print """

        test_delete_server_specify_string_to_server_id

        """
        resp, _ = self.ss_client.delete_server('server_id')
        print "resp=", resp
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_negative_to_server_id(self):
        print """

        test_delete_server_specify_negative_to_server_id

        """
        resp, _ = self.ss_client.delete_server(-1)
        print "resp=", resp
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_overlimits_to_server_id(self):
        print """

        test_delete_server_specify_overlimits_to_server_id

        """
        resp, _ = self.ss_client.delete_server(sys.maxint + 1)
        print "resp=", resp

        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_when_create_image(self):
        print """

        test_delete_server_when_create_image

        """
        self._test_delete_server_403_base('active', 'image_snapshot')

    @attr(kind='medium')
    def test_delete_server_specify_uuid(self):
        print """

        test_delete_server_specify_uuid

        """
        server = self.get_instance()
        uuid = server['uuid']
        resp, _ = self.ss_client.delete_server(uuid)
        print "resp=", resp
        self.assertEqual('204', resp['status'])
        self.ss_client.wait_for_server_not_exists(server['id'])
        resp, _ = self.ss_client.get_server(server['id'])
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def _test_delete_server_base(self, vm_state, task_state):
        # create server
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

        # status update
        self.update_status(server['id'], vm_state, task_state)

        # test for delete server
        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
        self.assertEqual('204', resp['status'])

        self.ss_client.wait_for_server_not_exists_ignore_error(server['id'])

        sql = ("SELECT deleted, vm_state, task_state "
               "FROM instances WHERE id = %s;") % (server['id'])
        rs = self.get_data_from_mysql(sql)
        (deleted, vm_state, task_state) = rs[:-1].split('\t')
        self.assertEqual('1', deleted)
        self.assertEqual('deleted', vm_state)
        self.assertEqual('NULL', task_state)

    @attr(kind='medium')
    def _test_delete_server_403_base(self, vm_state, task_state):
        # create server
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

        # status update
        self.update_status(server['id'], vm_state, task_state)

        # test for delete server
        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        self.assertEqual('403', resp['status'])

        # cleanup undeleted server
        sql = ("UPDATE instances SET "
               "deleted = 1, "
               "vm_state = 'deleted', "
               "task_state = NULL "
               "WHERE id = %s;") % server['id']
        self.exec_sql(sql)

        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            # if instance is shut off, line contains four element.
            # so, ignore it.
            try:
                (id, name, state) = line.split()
                if state == 'running':
                    subprocess.check_call('virsh destroy %s' % id, shell=True)
                subprocess.check_call('virsh undefine %s' % name, shell=True)
            except Exception:
               pass

    @attr(kind='medium')
    def test_delete_server_instance_vm_building_task_networking(self):
        self._test_delete_server_base('building', 'networking')

    @attr(kind='medium')
    def test_delete_server_instance_vm_building_task_bdm(self):
        self._test_delete_server_base('building', 'block_device_mapping')

    @attr(kind='medium')
    def test_delete_server_instance_vm_building_task_spawning(self):
        self._test_delete_server_base('building', 'spawning')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_image_backup(self):
        self._test_delete_server_base('active', 'image_backup')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_rebuilding(self):
        self._test_delete_server_base('active', 'rebuilding')

    @attr(kind='medium')
    def test_delete_server_instance_vm_error_task_building(self):
        self._test_delete_server_base('error', 'building')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_prep(self):
        self._test_delete_server_403_base('resizing', 'resize_prep')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_migrating(self):
        self._test_delete_server_403_base('resizing', 'resize_migrating')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_migrated(self):
        self._test_delete_server_403_base('resizing', 'resize_migrated')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_finish(self):
        self._test_delete_server_403_base('resizing', 'resize_finish')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_reverting(self):
        self._test_delete_server_403_base('resizing', 'resize_reverting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_resize_confirming(self):
        self._test_delete_server_403_base('resizing', 'resize_confirming')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_resize_verify(self):
        self._test_delete_server_403_base('active', 'resize_verify')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_rebooting(self):
        self._test_delete_server_403_base('active', 'rebooting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_building_task_deleting(self):
        self._test_delete_server_403_base('building', 'deleting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_deleting(self):
        self._test_delete_server_403_base('active', 'deleting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_error_task_none(self):
        self._test_delete_server_base('error', None)

    @attr(kind='medium')
    def test_delete_server_instance_vm_migrating_task_none(self):
        self._test_delete_server_403_base('migrating', None)

    @attr(kind='medium')
    def test_delete_server_instance_vm_resizing_task_none(self):
        self._test_delete_server_403_base('resizing', None)

    @attr(kind='medium')
    def test_delete_server_instance_vm_error_task_resize_prep(self):
        self._test_delete_server_base('error', 'resize_prep')

    @attr(kind='medium')
    def test_delete_server_instance_vm_error_task_error(self):
        self._test_delete_server_base('error', 'error')

    @attr(kind='medium')
    def test_delete_server_specify_uuid_more_than_37_char(self):
        print """

        test_delete_server_specify_uuid_more_than_37_char

        """
        uuid = 'a' * 37
        resp, _ = self.ss_client.delete_server(uuid)
        print "resp=", resp
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_uuid_less_than_35_char(self):
        print """

        test_update_server_specify_uuid_less_than_35_char

        """
        uuid = 'a' * 35
        resp, _ = self.ss_client.delete_server(uuid)
        print "resp=", resp
        self.assertEqual('400', resp['status'])


class UpdateServerTest(FunctionalTest):
    def setUp(self):
        super(UpdateServerTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.s2_client = self.os2.servers_client
        self.img_client = self.os.images_client
        self.kp_client = self.os.keypairs_client

    @attr(kind='medium')
    def test_update_server(self):
        print """

        test_update_server

        """
        server = self.get_instance()

        alt_name = self._testMethodName + '_rename'

        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        self.assertEqual('200', resp['status'])
        print "resp=", resp
        print "body=", body

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_update_server_not_exists_id(self):
        print """

        test_update_server_not_exists_id

        """
        alt_name = self._testMethodName + '_rename'
        resp, body = self.ss_client.update_server(sys.maxint, name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_update_server_same_name(self):
        print """

        test_update_server_same_name

        """
        server = self.get_instance()
        alt_name = server['name']
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_update_server_empty_name(self):
        print """

        test_update_server_empty_name

        """
        server = self.get_instance()
        alt_name = ''
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.656')
    @attr(kind='medium')
    def test_update_server_specify_other_tenant_server(self):
        print """

        test_update_server_specify_other_tenant_server

        """
        server = self.get_instance()
        # update server => tenant:demo
        alt_name = self._testMethodName + '_rename'
        resp, body = self.s2_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_overlimits_to_name(self):
        print """

        test_update_server_specify_overlimits_to_name

        """
        server = self.get_instance()

        alt_name = 'a' * 256
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])

    @test.skip_test('ignore this case for bug.658')
    @attr(kind='medium')
    def test_update_server_when_create_image(self):
        print """

        test_update_server_when_create_image

        """
        server = self.get_instance()
        # snapshot.
        img_name = self._testMethodName + '_image'
        resp, _ = self.ss_client.create_image(server['id'], img_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

        # update server
        alt_name = self._testMethodName + '_rename'
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('409', resp['status'])

        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

    @attr(kind='medium')
    def test_update_server_specify_uuid(self):
        print """

        test_update_server_specify_uuid

        """
        server = self.get_instance()
        uuid = server['uuid']
        alt_name = self._testMethodName + '_rename'
        resp, body = self.ss_client.update_server(uuid, name=alt_name)
        self.assertEqual('200', resp['status'])
        print "resp=", resp
        print "body=", body

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_update_server_specify_uuid_more_than_37_char(self):
        print """

        test_update_server_specify_uuid_more_than_37_char

        """
        #uuid = 'a' * 37
        alt_name = self._testMethodName + '_rename'
        #resp, body = self.ss_client.update_server(uuid, name=alt_name)
        resp, body = self.ss_client.update_server(100, name=alt_name)
        print "resp=", resp
        print "body=", body
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_uuid_less_than_35_char(self):
        print """

        test_update_server_specify_uuid_less_than_35_char

        """
        uuid = 'a' * 35
        alt_name = self._testMethodName + '_rename'
        resp, body = self.ss_client.update_server(uuid, name=alt_name)
        print "resp=", resp
        print "body=", body
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_double_byte(self):
        print """

        test_update_server_specify_double_byte

        """
        server = self.get_instance()
        alt_name = '\xef\xbb\xbf'

        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body
        self.assertEqual('500', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_illegal_characters(self):
        print """

        test_update_server_specify_illegal_characters

        """
        server = self.get_instance()
        alt_name = 'name_/.\@_name'

        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])

    @attr(kind='medium')
    def test_update_server_name_is_num(self):
        print """

        test_update_server_specify_illegal_characters

        """
        server = self.get_instance()
        alt_name = 999

        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body
        self.assertEqual('400', resp['status'])
