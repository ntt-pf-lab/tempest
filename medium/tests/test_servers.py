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
test_config = storm.config.StormConfig('etc/medium_test.conf')
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
    config2 = test_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.os2 = openstack.Manager(config=self.config2)
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
        subprocess.check_call('bin/nova-manage db sync',
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
                              '--label=private_1-3 '
                              '--project_id=1 '
                              '--fixed_range_v4=10.0.2.0/24 '
                              '--bridge_interface=br-int '
                              '--num_networks=1 '
                              '--network_size=32 ',
                              cwd=self.config.nova.directory, shell=True)
        subprocess.check_call('bin/nova-manage network create '
                              '--label=private_2-1 '
                              '--project_id=2 '
                              '--fixed_range_v4=10.0.3.0/24 '
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

#        self.output_eventlog()

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

    def output_eventlog(self):
        logfile_name = self._testMethodName + ".log"
        sql = "select * from eventlog;"
        rs = self.get_data_from_mysql(sql)
        if rs:
            with open(logfile_name, 'w') as logfile:
                for eventlog in rs.split('\n'):
                        logfile.write(eventlog)


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
               "WHERE id = %s;"
               ) % (deleted, vm_state, task_state, server_id)
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
        name = rand_name('server')
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
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name,
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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        for i in range(0, 3):
            resp, server = self.ss_client.create_server(
                                                name,
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
            self.assertEqual('ACTIVE', body['status'][i]['accessIPv4'])

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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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

        print """

        list servers with detail. not wait for server status is deleted.

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
        name = rand_name('server')
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

        list servers with detail. wait for server status is deleted.

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
        name = rand_name('server')
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
        alt_name = rand_name('server')
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
        resp, server = self.ss_client.create_server(name,
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

        sql = ("delete from images where id = " + alt_img_id + ";"
               "delete from image_properties where image_id = " + \
               alt_img_id + ";")
        self.exec_sql(sql, db='glance')

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
        name = rand_name('server')
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
        resp, body = self.ss_client.list_servers({'image': 99})
        print "resp=", resp
        print "body=", body
        self.assertEqual('200', resp['status'])
        self.assertEqual([], body['servers'])

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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('400', resp['status'])

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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_image(self):
        print """

        test_list_servers_specify_negative_to_image

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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_flavor(self):
        print """

        test_list_servers_specify_exists_flavor

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

    @attr(kind='medium')
    def test_list_servers_specify_not_exists_flavor(self):
        print """

        test_list_servers_specify_not_exists_flavor

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.list_servers({'flavor': 99})
        print "resp=", resp
        print "body=", body
        # Bug.605
        self.assertEqual('404', resp['status'])
#        self.assertEqual('200', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_string_to_flavor(self):
        print """

        test_list_servers_specify_string_to_flavor

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
        # Bug.605
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_flavor(self):
        print """

        test_list_servers_specify_overlimits_to_flavor

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
        # Bug.605
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_flavor(self):
        print """

        test_list_servers_specify_negative_to_flavor

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
        # Bug.605
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_exists_server_name(self):
        print """

        test_list_servers_specify_exists_server_name

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        name2 = rand_name('server')
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
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_list_servers_specify_empty_to_server_name(self):
        print """

        test_list_servers_specify_empty_to_server_name

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
        # Bug.606
        self.assertEqual('200', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_server_name(self):
        print """

        test_list_servers_specify_overlimits_to_server_name

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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_num_to_server_name(self):
        print """

        test_list_servers_specify_num_to_server_name

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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_status_active(self):
        print """

        test_list_servers_specify_status_active

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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_num_to_status(self):
        print """

        test_list_servers_specify_num_to_status

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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_list_servers_specify_string_to_limits(self):
        print """

        test_list_servers_specify_string_to_limits

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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('400', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_negative_to_limits(self):
        print """

        test_list_servers_specify_negative_to_limits

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
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_list_servers_specify_overlimits_to_limits(self):
        print """

        test_list_servers_specify_overlimits_to_limits

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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_list_servers_specify_change_since(self):
        print """

        test_list_servers_specify_change_since(Bug605)

        """
#        meta = {'hello': 'world'}
#        accessIPv4 = '1.1.1.1'
#        accessIPv6 = '::babe:220.12.22.2'
#        name = rand_name('server')
#        file_contents = 'This is a test file.'
#        personality = [{'path': '/etc/test.txt',
#                       'contents': base64.b64encode(file_contents)}]
#        resp, server = self.ss_client.create_server(name,
#                                                    self.image_ref,
#                                                    self.flavor_ref,
#                                                    meta=meta,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        # Wait for the server to become active
#        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
#
#        meta = {'hello': 'world'}
#        accessIPv4 = '1.1.1.2'
#        accessIPv6 = '::babe:220.12.22.3'
#        name = rand_name('server')
#        file_contents = 'This is a test file.'
#        personality = [{'path': '/etc/test.txt',
#                       'contents': base64.b64encode(file_contents)}]
#        resp, server = self.ss_client.create_server(name,
#                                                    self.image_ref,
#                                                    self.flavor_ref,
#                                                    meta=meta,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        # Wait for the server to become active
#        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
#
#        resp, _ = self.ss_client.delete_server(server['id'])
#        self.ss_client.wait_for_server_not_exists(server['id'])
#
#        resp, body = self.ss_client.list_servers(
#                                    {'changes-since': '2011-01-01T12:34Z'})
#        print "resp=", resp
#        print "body=", body
#        self.assertEqual('200', resp['status'])
#        self.assertEqual(2, len(body['servers']))

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
        name = rand_name('server')
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
        # Bug.605
        self.assertEqual('400', resp['status'])

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

        name_demo = rand_name('server')
        resp, server = self.s2_client.create_server(name_demo,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')

        # server2 => tenant:admin
        name_admin = rand_name('server')
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
        # bug.605
        self.assertEqual('200', resp['status'])
#        self.assertEqual('401', resp['status'])

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
        name = rand_name('server')
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
        alt_name = rand_name('server')
        resp, body = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('202', resp['status'])

        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

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
        self.assertEquals('400', resp['status'])

        sql = ("delete from images where id = " + alt_img_id + ";"
               "delete from image_properties where image_id = " + \
               alt_img_id + ";")
        self.exec_sql(sql, db='glance')

    @attr(kind='medium')
    def test_create_server_any_name(self):
        print """

        test_create_server_any_name

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
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_server_specify_exists_image(self):
        print """

        test_create_server_specify_exists_image

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

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_image(self):
        print """

        test_create_servers_specify_not_exists_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        image_ref = 99
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

    @attr(kind='medium')
    def test_create_servers_not_specify_image(self):
        """Ensure return error code 400 when not specify image"""
        print """

        test_list_servers_not_specify_image

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_invalid_fixed_ip_address(self):
        print """

        test_create_servers_specify_invalid_fixed_ip_address
        """

        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_invalid_uuid(self):
        print """

        test_create_servers_specify_invalid_uuid

        """

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_server_specify_exists_flavor(self):
        print """

        test_create_server_specify_exists_flavor

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

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_flavor(self):
        print """

        test_create_servers_specify_not_exists_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        flavor_ref = 99
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

    @attr(kind='medium')
    def test_create_servers_not_specify_flavor(self):
        print """

        test_create_servers_not_specify_flavor

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_networks(self):
        print """

        test_create_servers_specify_not_exists_networks

        """
        uuid = '12345678-90ab-cdef-fedc-ba0987654321'
        sql = "select uuid from networks where uuid = '" + uuid + "';"
        rs = self.get_data_from_mysql(sql)
        self.assertEqual(0, len(rs))

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_keypair(self):
        print """

        test_create_servers_specify_keypair

        """

        # create keypair
        keyname = rand_name('key')
        resp, keypair = self.kp_client.create_keypair(keyname)
        resp, body = self.os.keypairs_client.list_keypairs()

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_keypair(self):
        print """

        test_create_servers_specify_not_exists_keypair

        """

        # create keypair
        keyname = rand_name('key')
#        resp, keypair = self.kp_client.create_keypair(keyname)
#        resp, body = self.os.keypairs_client.list_keypairs()

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_server_specify_other_tenant_image(self):
        print """

        test_create_server_specify_other_tenant_image

        """

        # create server => tenant:admin
        name = rand_name('server')
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
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        # create server => tenant:demo
        demo_name = rand_name('server')
        resp, server = self.s2_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        print "resp=", resp
        print "body=", server
        # Bug.649
        self.assertEqual('400', resp['status'])
#        self.assertEqual('403', resp['status'])

        sql = ("delete from images where id = " + alt_img_id + ";"
               "delete from image_properties where image_id = " + \
               alt_img_id + ";")
        self.exec_sql(sql, db='glance')

    @attr(kind='medium')
    def test_create_servers_specify_networks(self):
        print """

        test_create_servers_specify_networks

        """

        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = rand_name('server')
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

    @attr(kind='medium')
    def test_create_servers_specify_three_networks(self):
        print """

        test_create_servers_specify_three_networks
        """

        sql = 'select uuid from networks where project_id = 1 limit 3;'
        uuids = self.get_data_from_mysql(sql)
        uuid = []
        for id in uuids.split('\n'):
            print "id=", id
            if id:
                uuid.append(id)

        meta = {'hello': 'world'}
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        networks = [{'fixed_ip': '10.0.0.2', 'uuid': uuid[0]},
                    {'fixed_ip': '10.0.1.2', 'uuid': uuid[1]},
                    {'fixed_ip': '10.0.2.2', 'uuid': uuid[2]}]
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

    @attr(kind='medium')
    def test_create_servers_specify_already_used_uuid(self):
        print """

        test_create_servers_specify_already_used_uuid

        """
        sql = 'select uuid from networks limit 1;'
        uuid = self.get_data_from_mysql(sql)
        uuid = uuid[:-1]

        meta = {'hello': 'world'}
        name = rand_name('server')
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
        print "resp=", resp
        print "server=", server

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        meta = {'hello': 'world'}
        name = rand_name('server')
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
        print "resp=", resp
        print "server=", server

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_ip_in_networks(self):
        print """

        test_create_servers_specify_not_exists_ip_in_networks(Bug.651)

        """

#        sql = 'select uuid from networks limit 1;'
#        uuid = self.get_data_from_mysql(sql)
#        uuid = uuid[:-1]
#
#        meta = {'hello': 'world'}
#        name = rand_name('server')
#        file_contents = 'This is a test file.'
#        personality = [{'path': '/etc/test.txt',
#                       'contents': base64.b64encode(file_contents)}]
#        networks = [{'fixed_ip': '192.168.0.1',
#                     'uuid':uuid}]
#        resp, body = self.ss_client.create_server_kw(name=name,
#                                                     imageRef=self.image_ref,
#                                                     flavorRef=self.flavor_ref,
#                                                     metadata=meta,
#                                                     networks=networks,
#                                                     personality=personality)
#
#        print "resp=", resp
#        print "body=", body
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_create_servers_specify_not_exists_zone(self):
        print """

        test_create_servers_specify_not_exists_zone

        """

        zone = rand_name('zone:')

        meta = {'hello': 'world'}
        name = rand_name('server')
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
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_create_servers_specify_exists_zone(self):
        print """

        test_create_servers_specify_exists_zone

        """

        sql = "insert into zones (deleted, api_url) values(0, 'zone');"
        self.exec_sql(sql)
        zone = 'zone'

        meta = {'hello': 'world'}
        name = rand_name('server')
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
        self.assertEqual('202', resp['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(body['id'], 'ACTIVE')
        resp, body = self.ss_client.get_server(body['id'])
        print "body=", body
        self.assertEqual('200', resp['status'])

        sql = "delete from zones;"
        self.exec_sql(sql)

    @attr(kind='medium')
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
        name = rand_name('server')
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
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
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

        resp, server = self.ss_client.create_server(name,
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

        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        print "resp=", resp
        print "server=", server
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_create_server_quota_memory(self):
        print """

        test_create_server_quota_memory(#619)

        """

#        sql = ('INSERT INTO quotas(deleted, project_id, resource, hard_limit)'
#               "VALUES(0, '1', 'ram', 1)")
#        self.exec_sql(sql)
#
#        print """
#
#        creating server.
#
#        """
#        accessIPv4 = '1.1.1.1'
#        accessIPv6 = '::babe:220.12.22.2'
#        name = rand_name('server')
#        file_contents = 'This is a test file.'
#        personality = [{'path': '/etc/test.txt',
#                       'contents': base64.b64encode(file_contents)}]
#        resp, server = self.s2_client.create_server(name,
#                                                    self.image_ref,
#                                                    self.flavor_ref,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        print "resp=", resp
#        print "server=", server
#        self.assertEqual('202', resp['status'])
#
#        # Wait for the server to become active
#        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')
#
#        resp, server = self.s2_client.create_server(name,
#                                                    self.image_ref,
#                                                    self.flavor_ref,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        print "resp=", resp
#        print "server=", server
#        self.assertEqual('202', resp['status'])
#
#        # Wait for the server to become active
#        self.s2_client.wait_for_server_status(server['id'], 'ACTIVE')
#
#        resp, server = self.s2_client.create_server(name,
#                                                    self.image_ref,
#                                                    self.flavor_ref,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        print "resp=", resp
#        print "server=", server
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_create_server_quota_disk(self):
        print """

        test_create_server_quota_disk(Bug.619)

        """

#        sql = ('INSERT INTO quotas(deleted, project_id, resource, hard_limit)'
#               "VALUES(0, 'admin', 'gigabyte', 1)")
#        self.exec_sql(sql)
#
#        print """
#
#        creating server.
#
#        """
#        accessIPv4 = '1.1.1.1'
#        accessIPv6 = '::babe:220.12.22.2'
#        name = rand_name('server')
#        file_contents = 'This is a test file.'
#        personality = [{'path': '/etc/test.txt',
#                       'contents': base64.b64encode(file_contents)}]
#        resp, server = self.ss_client.create_server(name,
#                                                    self.image_ref,
#                                                    2,
#                                                    accessIPv4=accessIPv4,
#                                                    accessIPv6=accessIPv6,
#                                                    personality=personality)
#
#        print "resp=", resp
#        print "server=", server
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_by_id(self):
        print """

        test_get_server_details_by_id

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body

        self.assertEqual('200', resp['status'])
        self.assertEqual(name, body['name'])

    @attr(kind='medium')
    def test_get_server_details_by_uuid(self):
        print """

        test_get_server_details_by_uuid

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

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
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

        self.assertNotEqual(99, server['id'])
        resp, body = self.ss_client.get_server(99)
        print "resp=", resp
        print "body=", body

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_other_tenant_server(self):
        print """

        test_get_server_details_specify_other_tenant_server

        """

        # create server => tenant:admin
        name = rand_name('server')
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

        # get server => tenant:demo
        resp, body = self.s2_client.get_server(server['id'])
        print "resp=", resp
        print "body=", body
        # Bug.622
        self.assertEqual('404', resp['status'])
#        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_string_to_id(self):
        print """

        test_get_server_details_specify_string_to_id

        """
        resp, body = self.ss_client.get_server('abcdefghij')
        print "resp=", resp
        print "body=", body

        # Bug.623
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_negative_to_id(self):
        print """

        test_get_server_details_specify_negative_to_id

        """
        resp, body = self.ss_client.get_server(-1)
        print "resp=", resp
        print "body=", body
        # Bug.624
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_server_details_specify_overlimits_to_id(self):
        print """

        test_get_server_details_specify_overlimits_to_id

        """
        resp, body = self.ss_client.get_server(sys.maxint + 1)
        print "resp=", resp
        print "body=", body

        # Bug.625
        self.assertEqual('404', resp['status'])
        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_update_server(self):
        print """

        test_update_server

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name, body['name'])

        alt_name = rand_name('server')
        self.assertNotEqual(name, alt_name)

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
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

        alt_name = rand_name('server')
        self.assertNotEqual(name, alt_name)
        self.assertNotEqual(99, server['id'])
        resp, body = self.ss_client.update_server(99, name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_update_server_same_name(self):
        print """

        test_update_server_same_name

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name1 = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name1,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        name2 = rand_name('server')
        resp, server = self.ss_client.create_server(name2,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name2, body['name'])

        alt_name = name1
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
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name, body['name'])

        alt_name = ''
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_other_tenant_server(self):
        print """

        test_update_server_specify_other_tenant_server

        """

        # create server => tenant:admin
        name = rand_name('server')
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

        # update server => tenant:demo
        alt_name = rand_name('server')
        self.assertNotEqual(name, alt_name)
        resp, body = self.s2_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        # Bug.656
        self.assertEqual('404', resp['status'])
#        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_update_server_specify_overlimits_to_name(self):
        print """

        test_update_server_specify_overlimits_to_name

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(name, body['name'])

        alt_name = 'a' * 256
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        # Bug.657
        self.assertEqual('200', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_update_server_when_create_image(self):
        print """

        test_update_server_when_create_image

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # snapshot.
        img_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], img_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

        # update server
        alt_name = rand_name('server')
        resp, body = self.ss_client.update_server(server['id'], name=alt_name)
        print "resp=", resp
        print "body=", body

        # Bug.658
        self.assertEqual('200', resp['status'])
        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])
#        self.assertEqual('409', resp['status'])

        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        sql = ("delete from images where id = " + alt_img_id + ";"
               "delete from image_properties where image_id = " + \
               alt_img_id + ";")
        self.exec_sql(sql, db='glance')

    @attr(kind='medium')
    def test_update_server_specify_uuid(self):
        print """

        test_update_server_specify_uuid

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        uuid = body['uuid']
        alt_name = rand_name('server')
        resp, body = self.ss_client.update_server(uuid, name=alt_name)
        self.assertEqual('200', resp['status'])
        print "resp=", resp
        print "body=", body

        resp, body = self.ss_client.get_server(server['id'])
        self.assertEqual(alt_name, body['name'])

    @attr(kind='medium')
    def test_delete_server(self):
        print """

        test_delete_server

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

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
        resp = self.ss_client.delete_server(99)
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
        name = rand_name('server')
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
    def test_delete_server_when_server_is_deleting(self):
        print """

        test_delete_server_when_server_is_deleting

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

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
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
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

        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        # Bug.668
        self.assertEqual('404', resp['status'])
        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_other_tenant_server(self):
        print """

        test_delete_server_specify_other_tenant_server

        """

        # create server => tenant:admin
        name = rand_name('server')
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

        # delete server => tenant:demo
        resp, _ = self.s2_client.delete_server(server['id'])
        print "resp=", resp
        # Bug.662
        self.assertEqual('404', resp['status'])
#        self.assertEqual('403', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_string_to_server_id(self):
        print """

        test_delete_server_specify_string_to_server_id

        """
        resp, _ = self.ss_client.delete_server('server_id')
        print "resp=", resp
        # Bug.662
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_negative_to_server_id(self):
        print """

        test_delete_server_specify_negative_to_server_id

        """
        resp, _ = self.ss_client.delete_server(-1)
        print "resp=", resp
        # Bug.662
        self.assertEqual('404', resp['status'])
#        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_server_specify_overlimits_to_server_id(self):
        print """

        test_delete_server_specify_overlimits_to_server_id

        """
        resp, _ = self.ss_client.delete_server(sys.maxint + 1)
        print "resp=", resp

        # Bug.662
        self.assertEqual('404', resp['status'])
#        self.assertEqual('413', resp['status'])

    @attr(kind='medium')
    def test_delete_server_when_create_image(self):
        print """

        test_delete_server_when_create_image

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # snapshot.
        img_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], img_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']

        # delete server
        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
#        resp, body = self.ss_client.get_server(server['id'])
#        self.assertEqual(name, body['name'])

        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')

        sql = ("delete from images where id = " + alt_img_id + ";"
               "delete from image_properties where image_id = " + \
               alt_img_id + ";")
        self.exec_sql(sql, db='glance')

    @attr(kind='medium')
    def test_delete_server_specify_uuid(self):
        print """

        test_delete_server_specify_uuid

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
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        resp, body = self.ss_client.get_server(server['id'])
        uuid = body['uuid']
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
        name = rand_name('server')
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

        self.ss_client.wait_for_server_not_exists(server['id'])

        sql = ("SELECT deleted, vm_state, task_state "
               "FROM instances WHERE id = %s;"
               ) % (server['id'])
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
        name = rand_name('server')
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

        # Bug.687
#        self.assertEqual('403', resp['status'])

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
    def test_delete_server_instance_vm_active_task_rebooting(self):
        self._test_delete_server_403_base('active', 'rebooting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_reboot_task_rebooting(self):
        self._test_delete_server_403_base('reboot', 'rebooting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_building_task_deleting(self):
        self._test_delete_server_403_base('building', 'deleting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_active_task_deleting(self):
        self._test_delete_server_403_base('active', 'deleting')

    @attr(kind='medium')
    def test_delete_server_instance_vm_error_task_error(self):
        self._test_delete_server_403_base('error', 'error')
