import base64
import re
import subprocess
import time
import json

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

# for admin tenant
default_config = storm.config.StormConfig('etc/medium.conf')
# for demo tenant
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
        # for admin tenant
        self.os = openstack.Manager(config=self.config)
        # for demo tenant
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


class ServersTest(FunctionalTest):
    def setUp(self):
        super(ServersTest, self).setUp()
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
        resp, server = self.ss_client.create_server(name,
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
               "WHERE id = %s;"
               ) % (deleted, vm_state, task_state, server['id'])
        self.exec_sql(sql)

        return server['id']

    @attr(kind='medium')
    def _test_reboot_403_base(self, vm_state, task_state, deleted=0):
        server_id = self.create_dummy_instance(vm_state, task_state, deleted)
        resp, _ = self.ss_client.reboot(server_id, 'HARD')
        self.assertEquals('403', resp['status'])

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
        test_id = 5
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
        name = rand_name('instance')
        file_contents = 'This is a test_file.'
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
        test_id = server['uuid']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('2.2.2.2', server['accessIPv4'])
        self.assertEqual('::babe:330.23.33.3', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

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
        name = rand_name('server')
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
        resp, server = self.ss_client.reboot(invalid_test_id, 'HARD')
        self.assertEquals('400', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_specify_negative_number_as_id(self):

        print """

        reboot server

         """

        reboot_id = -1
        resp, server = self.ss_client.reboot(reboot_id, 'HARD')
        self.assertEquals('400', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_id_is_over_max_int(self):

        print """

        reboot server

         """

        reboot_id = 2147483648
        resp, server = self.ss_client.reboot(reboot_id, 'HARD')
        print "resp=", resp
        self.assertEquals('400', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_running(self):

        print """

        creating server.

        """
        meta = {'hello': 'opst'}
        accessIPv4 = '2.2.2.2'
        accessIPv6 = '::babe:330.23.33.3'
        name = rand_name('instance')
        file_contents = 'This is a test_file.'
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
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('2.2.2.2', server['accessIPv4'])
        self.assertEqual('::babe:330.23.33.3', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('200', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_during_reboot_process(self):

        print """

        creating server.

        """
        meta = {'open': 'stack'}
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
        test_id = server['id']

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')

        print """

        reboot server without waiting done creating

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')
        self.assertEquals('202', resp['status'])
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('REBOOT', server['status'])

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEquals('ACTIVE', server['status'])

#    @attr(kind='medium')
#    def test_reboot_when_server_is_during_stop_process(self):
#
#        print """
#
#        creating server.
#
#        """
#        meta = {'open': 'stack'}
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
#        test_id = server['id']
#        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')
#
#        print """
#
#        deleting server
#
#         """
#        # Stop server
#        resp, server = self.ss_client.delete_server(test_id)
#
#        print """
#
#        reboot server without waiting done stopping
#
#         """
#
#        # Reboot stopped server
#        resp, server = self.ss_client.reboot(test_id, 'HARD')
#        self.assertEquals('202', resp['status'])
#        resp, server = self.ss_client.get_server(test_id)
#        self.assertEquals('REBOOT', server['status'])
#
#        sql = ("SELECT deleted FROM instances WHERE id=" + test_id + ";")
#        sql_resp = self.get_data_from_mysql(sql)
#        sql_resp = sql_resp.split('\n')
#        while sql_resp != '1':
#            sql_resp = self.get_data_from_mysql(sql)
#            sql_resp = sql_resp.split('\n')
#
#        resp, body = self.ss_client.get_server(test_id)
#        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_reboot_when_server_is_down(self):
        print """

        creating server.

        """
        meta = {'open': 'stack'}
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
        test_id = server['id']
        self.ss_client.wait_for_server_status(test_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(test_id)
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
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image(self):

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

    @attr(kind='medium')
    def test_create_image_when_specify_server_by_uuid(self):

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
        test_uuid = server['uuid']
        resp, body = self.ss_client.create_image(test_uuid, alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, image = self.img_client.get_image(alt_img_id)
        self.assertEquals('ACTIVE', image['status'])

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
        resp, _ = self.ss_client.create_image(99, 'opst_test')
        self.assertEquals('404', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_specify_server_of_another_tenant(self):

        print """

        creating server of admin(is admin).

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
        resp, body = self.s2_client.create_image(test_server_id, alt_name)
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_during_boot_process(self):

        print """

        creating server.

        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.2.3.4'
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

        resp, server = self.ss_client.get_server(server['id'])
        test_id = server['id']
        self.assertEquals('BUILD', server['status'])

        print """

        creating snapshot without waiting done creating server.

        """
        # Make snapshot without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_during_reboot_process(self):

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
        test_id = server['id']

        print """

        reboot server

         """
        resp, server = self.ss_client.reboot(test_id, 'HARD')

        print """

        creating snapshot without waiting done rebooting server.

        """
        alt_name = rand_name('opst')
        resp, body = self.ss_client.create_image(test_id, alt_name)
        self.assertEquals('403', resp['status'])

    @attr(kind='medium')
    def test_create_image_when_server_is_during_stop_process(self):

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
        test_server_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_server_id)
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
        self.assertEquals('404', resp['status'])
        self.ss_client.wait_for_server_not_exists(test_server_id)

    @attr(kind='medium')
    def test_create_image_when_server_is_down(self):

        print """

        creating server.

        """
        meta = {'opst': 'testing'}
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
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_server_id)
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
        resp, servers = self.ss_client.list_servers()
        self.assertEquals([], servers['servers'])

        print """

        creating snapshot.

        """
        # Make snapshot of the instance without waiting done creating server
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(test_server_id, alt_name)
        print "resp=", resp
        self.assertEquals('403', resp['status'])

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_name)
        self.img_client.wait_for_image_not_exists(alt_name)

    @attr(kind='medium')
    def test_create_image_when_other_image_is_during_saving_process(self):

        print """

        creating server.

        """
        meta = {'aaaaa': 'bbbbb'}
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
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('ACTIVE', server['status'])

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_server_id)
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
        resp1, body1 = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals('202', resp['status'])

        print """

        creating snapshot again during the other one is
                                                during process of image saving.

        """
        # Make snapshot of the instance.
        alt_test_name = rand_name('server_2')
        resp2, body2 = self.ss_client.create_image(test_server_id,
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
    def test_create_img_when_server_has_not_enough_capacity_to_save_img(self):

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

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        print """

        creating snapshot.

        """

    @attr(kind='medium')
    def test_create_image_when_specify_duplicate_image_name(self):
        print """

        creating server.

        """
        meta = {'aaaaa': 'bbbbb'}
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
        test_server_id = server['id']
        self.ss_client.wait_for_server_status(test_server_id, 'ACTIVE')
        resp, server = self.ss_client.get_server(test_server_id)
        self.assertEquals('ACTIVE', server['status'])

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_server_id)
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
        resp1, body1 = self.ss_client.create_image(test_server_id, alt_name)
        self.assertEquals("202", resp1)

        alt_img_url = resp1['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, images = self.img_client.get_image(alt_img_id)
#        self.assertEquals('ACTIVE', images['status'])

        time.sleep(10)

        print """

        creating snapshot again.

        """
        # Make snapshot of the instance.
        alt_test_name = rand_name('server')
        resp2, body2 = self.ss_client.create_image(test_server_id,
                                                   alt_test_name)
        self.assertEquals("202", resp2)

        alt_test_img_url = resp2['location']
        match = re.search('/images/(?P<image_id>.+)', alt_test_img_url)
        self.assertIsNotNone(match)
        alt_test_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_test_img_id, 'ACTIVE')
        resp, images = self.img_client.get_image(alt_test_img_id)
#        self.assertEquals('ACTIVE', images['status'])

        time.sleep(20)

        print """

        creating server from snapshot.

        """
        resp, server = self.ss_client.create_server(name,
                                                    alt_test_img_id,
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
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
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
        resp, _ = self.ss_client.create_image(test_id, alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp, images = self.img_client.list_images()
        print "resp=", resp
        print "images=", images

        print """

        deleting snapshot.

        """
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)

    @attr(kind='medium')
    def test_create_image_when_metadata_exists(self):

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

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
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
        resp, body = self.ss_client.create_image(test_id, alt_name, meta)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp_wait, image_wait = self.img_client.get_image(alt_img_id)
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

    @attr(kind='medium')
    def test_create_image_when_key_and_value_are_blank(self):

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

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
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
        resp, body = self.img_client.create_image(test_id,
                                                  alt_name,
                                                  meta=meta)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        resp_wait, image_wait = self.img_client.get_image(alt_img_id)
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

    @attr(kind='medium')
    def test_ceate_image_when_specify_length_over_256_key_and_value(self):

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

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        test_id = server['id']

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(test_id)
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
        resp, body = self.ss_client.create_image(test_id, alt_name, meta=meta)
        print "resp=", resp
        print "body=", body
        self.assertEquals('202', resp['status'])
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
    def test_create_image_when_vm_eq_active_and_task_eq_updating_password(self):
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
