import os
import re
import subprocess
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
import storm.config
from storm import exceptions
from storm.common.utils.data_utils import rand_name
import stackmonkey.manager as ssh_manager
from nova import test

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess,
        FakeQuantumProcess)
from medium.tests.utils import (
        emphasised_print, silent_check_call,
        cleanup_virtual_instances, cleanup_processes)


config = storm.config.StormConfig('etc/medium-less-build_timeout.conf')
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

    for process in environ_processes:
        process.start()
    time.sleep(10)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class QuantumFunctionalTest(unittest.TestCase):

    config = config

    def setUp(self):
        emphasised_print(self.id())

        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaComputeProcess(
                self.config.nova.directory))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.nova.directory, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

        # create users.
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def check_create_network(self, retcode):
        self.assertEqual(subprocess.call('bin/nova-manage network create '
                                             '--label=private_1-1 '
                                             '--project_id=1 '
                                             '--fixed_range_v4=10.0.0.0/24 '
                                             '--bridge_interface=br-int '
                                             '--num_networks=1 '
                                             '--network_size=32 ',
                                         cwd=self.config.nova.directory,
                                         shell=True), retcode)

    def _execute_fake_and_wait_for_error(self, **param):
        # quantum.
        quantum = FakeQuantumProcess('1', **param)
        self.testing_processes.append(quantum)
        quantum.start()

        self.check_create_network(0)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        emphasised_print('Start testing %s' % self.id())
        quantum.set_test(True)

        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    def _test_show_port_attachment(self, status_code):
        self._execute_fake_and_wait_for_error(show_port_attachment=status_code)

    @attr(kind='medium')
    def test_show_port_attachment_forbidden(self):
        self._test_show_port_attachment(403)

    @attr(kind='medium')
    def test_show_port_attachment_network_not_found(self):
        self._test_show_port_attachment(420)

    @attr(kind='medium')
    def test_show_port_attachment_port_not_found(self):
        self._test_show_port_attachment(430)

    def _test_unplug_port_attachment(self, status_code):
        self._execute_fake_and_wait_for_error(
                unplug_port_attachment=status_code)

    @attr(kind='medium')
    def test_unplug_port_attachment_forbidden(self):
        self._test_unplug_port_attachment(403)

    @attr(kind='medium')
    def test_unplug_port_attachment_network_not_found(self):
        self._test_unplug_port_attachment(420)

    @attr(kind='medium')
    def test_unplug_port_attachment_port_not_found(self):
        self._test_unplug_port_attachment(430)

    def _test_delete_port(self, status_code):
        self._execute_fake_and_wait_for_error(delete_port=status_code)

    @attr(kind='medium')
    def test_delete_port_bad_request(self):
        self._test_delete_port(400)

    @attr(kind='medium')
    def test_delete_port_forbidden(self):
        self._test_delete_port(403)

    @attr(kind='medium')
    def test_delete_port_network_not_found(self):
        self._test_delete_port(420)

    @attr(kind='medium')
    def test_delete_port_port_not_found(self):
        self._test_delete_port(430)

    @attr(kind='medium')
    def test_delete_port_port_in_use(self):
        self._test_delete_port(432)


class LibvirtFunctionalTest(unittest.TestCase):

    config = config

    def tearDown(self):
        self._dumpdb()

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    def setUp(self):
        emphasised_print(self.id())

        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        # quantum.
        self.testing_processes.append(
                FakeQuantumProcess('1'))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.nova.directory, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # allocate networks.
        silent_check_call('bin/nova-manage network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 ',
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                '../../medium/tests/fakes',
                name)


class LibvirtErrorTest(LibvirtFunctionalTest):

    def _delete_server_with_fake_libvirt(self, fake_name, patches):

        compute = NovaComputeProcess(
                self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

        compute.stop()
        self.testing_processes.pop()
        # start fake nova-compute for libvirt error
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fake_name)
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

    @attr(kind='medium')
    def test_d02_223(self):
        self._delete_server_with_fake_libvirt('lookup-error', [
            ('libvirt', 'fake_libvirt.libvirt_patch_vir_error')])

    @attr(kind='medium')
    def test_d02_224(self):
        self._delete_server_with_fake_libvirt('lookup-error', [
            ('libvirt', 'fake_libvirt.libvirt_patch_no_domain')])

    @attr(kind='medium')
    def test_d02_226(self):
        self._delete_server_with_fake_libvirt('virdomain-error', [
            ('libvirt', 'fake_libvirt.libvirt_patch'),
            ('nova.virt.libvirt.connection', 'fake_libvirt_connection.patch')])

    @attr(kind='medium')
    def test_d02_227(self):
        self._delete_server_with_fake_libvirt('virdomain-error', [
            ('libvirt', 'fake_libvirt.libvirt_patch_invalid_operation')])

    @attr(kind='medium')
    def test_d02_229(self):
        self._delete_server_with_fake_libvirt('virdomain-error', [
            ('libvirt', 'fake_libvirt.libvirt_patch_undefine')])

    @attr(kind='medium')
    def test_d02_230(self):
        self._delete_server_with_fake_libvirt('virdomain-error', [
            ('libvirt', 'fake_libvirt.libvirt_undefine_patch_invalid_operation')])

    @test.skip_test('skip temply')
    @attr(kind='medium')
    def test_d02_232(self):
        self._delete_server_with_fake_libvirt('vif-unplug-error', [
            ('nova.virt.libvirt.vif', 'fake_libvirt_vif.vif_patch')])

    @test.skip_test('skip temply')
    @attr(kind='medium')
    def test_d02_234(self):
        self._delete_server_with_fake_libvirt('vif-unplug-error', [
            ('nova.virt.libvirt.vif', 'fake_libvirt_vif.vif_patch')])

    @test.skip_test('skip temply')
    @attr(kind='medium')
    def test_d02_236(self):
        self._delete_server_with_fake_libvirt('firewall-error', [
            ('nova.virt.libvirt.firewall', 'fake_iptables.unfilter_patch')])

    @test.skip_test('skip temply')
    @attr(kind='medium')
    def test_d02_237(self):
        self._delete_server_with_fake_libvirt('general-error', [
            ('shutil', 'fake.rmtree_patch')])

    'TODO: assert'
    @attr(kind='large')
    def test_d02_225(self):
        compute = NovaComputeProcess(self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

        compute.compute_havoc.stop_libvirt()

        self.ss_client.delete_server(server['id'])
        self.assertRaises(exceptions.TimeoutException,
                          self.ss_client.wait_for_server_not_exists(server['id']))

    'TODO: assert'
    @attr(kind='large')
    def test_d02_228(self):
        self._delete_server_with_fake_libvirt('fake_delete_server/virdomain-error',
            [('libvirt', 'fake_libvirt.libvirt_is_not_running_of_virt_dom_destroy_patch')])

    'TODO: assert'
    @attr(kind='large')
    def test_d02_231(self):
        
        self._delete_server_with_fake_libvirt('fake_delete_server/virdomain-error',
            [('libvirt', 'fake_libvirt.libvirt_is_not_running_of_virt_dom_undefine_patch')])

    'TODO: assert'
    @attr(kind='large')
    def test_d02_233(self):
        self._delete_server_with_fake_libvirt('vif-unplug-error', [
            ('nova.virt.libvirt.vif', 'fake_libvirt_vif.vif_no_answer_patch')])

    'TODO: assert'
    @attr(kind='large')
    def test_d02_235(self):
        self._delete_server_with_fake_libvirt('vif-plug-error', [
            ('nova.virt.libvirt.vif', 'fake_libvirt_vif.vif_no_answer_patch')])


class DBErrorTest(LibvirtFunctionalTest):

    def _create_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs):

        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.nova.directory + '/bin/nova.conf')

        compute.start()

        self.testing_processes.append(compute)
        time.sleep(10)

#        self.havoc._run_cmd("sudo service mysql stop")

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

    def _delete_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs):

        compute = NovaComputeProcess(
                self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

        compute.stop()
        self.testing_processes.pop()

        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
        compute = NovaApiProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.nova.directory + '/bin/nova.conf')

        compute.start()

        self.testing_processes.append(compute)
        time.sleep(10)
        
        resp, server = self.ss_client.delete_server(server['id'])


    def _create_server_with_down_glance(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ACTIVE'):

        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
#            ':/home/openstack/workspace/openstack-integration-tests'
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.nova.directory + '/bin/nova.conf')

        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], status)


class DbFunctionalTest(unittest.TestCase):

    config = config

    def tearDown(self):
        try:
            self.havoc._run_cmd("sudo service mysql start")
            time.sleep(10)
        except:
            pass
        self._dumpdb()

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    def setUp(self):
        emphasised_print(self.id())

        self.havoc = ssh_manager.HavocManager()
        self.ssh_con = self.havoc.connect('127.0.0.1', 'openstack',
                        'openstack', self.havoc.config.nodes.ssh_timeout)

        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
        self.testing_processes = []

        # nova.
#        self.testing_processes.append(NovaApiProcess(
#                self.config.nova.directory,
#                self.config.nova.host,
#                self.config.nova.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        # quantum.
        self.testing_processes.append(
                FakeQuantumProcess('1'))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.nova.directory, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)

        # allocate networks.
        silent_check_call('bin/nova-manage network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 ',
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)

    def get_tests_path(self, name):
        p = os.path.dirname(__file__)
        p = p.split(os.path.sep)[0:-2]
        return os.path.join(os.path.sep.join(p), name)

class DBError2Test(DbFunctionalTest):
    def _delete_server_with_fake_db_on_api(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs):

        # start nova-API for create server
        nova_api = NovaApiProcess(self.config.nova.directory,
                                  self.config.nova.host,
                                  self.config.nova.port)
        nova_api.start()
        self.testing_processes.append(nova_api)
        time.sleep(10)

        # start nova-compute
        compute = NovaComputeProcess(self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        _, server = self.ss_client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

        # Stop nova-api
        nova_api.stop()
        self.testing_processes.pop()

        # start fake nova-api for db error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
        nova_api = NovaApiProcess(self.config.nova.directory,
                                  self.config.nova.host,
                                  self.config.nova.port,
                                  patches=patches,
                                  env=env,
                    config_file=self.config.nova.directory + '/bin/nova.conf')

        nova_api.start()

        self.testing_processes.append(compute)
        time.sleep(10)

        resp,_ = self.ss_client.delete_server(server['id'])
        print "resp=", resp
#        return self.ss_client.delete_server(server['id'])

    def _delete_server_with_fake_db_on_compute(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ERROR'):

        # start nova-API
        nova_api = NovaApiProcess(self.config.nova.directory,
                                  self.config.nova.host,
                                  self.config.nova.port)
        nova_api.start()
        self.testing_processes.append(nova_api)
        time.sleep(10)

        # start nova-compute for create server
        compute = NovaComputeProcess(self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        _, server = self.ss_client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)

        # Wait for the server to become ACTIVE
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

        # Stop nova-compute
        compute.stop()
        self.testing_processes.pop()

        # start fake nova-compute for db error(DB STOP)
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.nova.directory + '/bin/nova.conf')

        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

#        self.ss_client.delete_server(server['id'])
        resp, _ = self.ss_client.delete_server(server['id'])
        print "resp=", resp

        # Stop fake nova-compute for remove the patch
        compute.stop()
        self.testing_processes.pop()

        # DB start
        rtn = self.havoc._run_cmd("sudo service mysql start")
        print "rtn=", rtn
        time.sleep(10)

        # nova-api reboot
        nova_api.stop()
        nova_api.start()

        # start nova-compute
        compute = NovaComputeProcess(self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        # Wait for the server until parm:status
        self.ss_client.wait_for_server_status(
                          server['id'], status)


    'TODO: test done'
    @attr(kind='large')
    def test_d02_201(self):
        resp, _ = self._delete_server_with_fake_db_on_api('nova.db.api',
                                                          'fake_delete_server',
                                              'db_error.db_get_stop_patch', [])
        self.assertEquals(resp['status'], '500')

    'TODO: test done'
    @attr(kind='large')
    def test_d02_202(self):
        resp, _ = self._delete_server_with_fake_db_on_api('nova.db.api',
                                                          'fake_delete_server',
                                    'db_error.db_get_stop_exception_patch', [])
        self.assertEquals(resp['status'], '500')

    'TODO: infinite loop'
    'TODO: TimeoutException?'
    @attr(kind='large')
    def test_d02_203(self):
        self.assertRaises(exceptions.TimeoutException,
                          self._delete_server_with_fake_db_on_compute,
                          'nova.db.api',
                          'fake_delete_server',
                          'db_error.get_vif_by_instance_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_204(self):
        self.assertRaises(exceptions.BuildErrorException,
                          self._delete_server_with_fake_db_on_compute,
                          'nova.db.api',
                          'fake_delete_server',
                          'db_error.get_vif_by_instance_exception_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_205(self):
        self.assertRaises(exceptions.BuildErrorException,
                          self._delete_server_with_fake_db_on_compute,
                          'nova.db.api',
                          'fake_delete_server',
                          'db_error.get_empty_vif_by_instance_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_238(self):
        self.assertRaises(TypeError,
            self._delete_server_with_fake_db_on_api_compute, 'nova.db.api', 'fake_delete_server',
                        'db-error.instance_update_delete_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_239(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._delete_server_with_fake_db_on_api, 'nova.db.api', 'db-error',
                        'fake_delete_server.instance_update_delete_exception_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_240(self):
        self.assertRaises(TypeError,
            self._delete_server_with_fake_db_on_api, 'nova.db.api', 'db-error',
                        'fake_delete_server.db_stop_patch', [])

    'TODO: preparing API'
    @attr(kind='large')
    def test_d02_241(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._delete_server_with_fake_db_on_api, 'nova.db.api', 'db-error',
                        'fake_delete_server.db_stop_exception_patch', [])

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_209(self):
        pass

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_210(self):
        pass

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_211(self):
        pass

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_212(self):
        pass

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_221(self):
        pass

    'TODO: Melange'
    @attr(kind='large')
    def test_d02_222(self):
        pass
