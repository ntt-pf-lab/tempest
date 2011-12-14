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
from nova import utils
from nova import flags

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
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

    def tearDown(self):
        self._dumpdb()

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
            'select id, instance_id, network_id, address, deleted '
            'from virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

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

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def check_create_network(self, retcode):
        self.assertEqual(subprocess.call('bin/nova-manage network create '
                                             '--label=private_1-1 '
                                             '--project_id=admin '
                                             '--fixed_range_v4=10.0.0.0/24 '
                                             '--bridge_interface=br-int '
                                             '--num_networks=1 '
                                             '--network_size=32 ',
                                         cwd=self.config.nova.directory,
                                         shell=True), retcode)

    def _execute_and_wait_for_error(self, **param):
        # quantum.
        quantum = QuantumProcess(self.config.quantum.directory,
                        self.config.quantum.config)
        quantum_plugin = QuantumPluginOvsAgentProcess(
                        self.config.quantum.directory,
                        self.config.quantum.agent_config)

        self.testing_processes.append(quantum)
        self.testing_processes.append(quantum_plugin)
        quantum.start()
        quantum_plugin.start()

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

        if param['delete_vif_db']:
            subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
                              'delete from fixed_ips;'
                              'delete from virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        self.ss_client.reboot(server['id'], 'HARD')
        # Wait for the server to become ERROR.DELETED
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    def _execute_fake_and_wait_for_error(self, **param):
        # quantum.
        quantum = FakeQuantumProcess('admin', **param)
#        quantum = FakeQuantumProcess(self.config.nova.tenant_name)
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

        self.ss_client.reboot(server['id'], 'HARD')
        # Wait for the server to become ERROR.DELETED
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    def _test_show_port_attachment(self, status_code):
        self._execute_fake_and_wait_for_error(show_port_attachment=status_code)

    @attr(kind='medium')
    def test_d02_310(self):
        self._execute_and_wait_for_error(delete_vif_db=True)

    @attr(kind='medium')
    def test_d02_311(self):
        """show_port_attachment_forbidden"""
        self._test_show_port_attachment(403)

    @attr(kind='medium')
    def test_d02_312(self):
        """show_port_attachment_network_not_found"""
        self._test_show_port_attachment(420)

    @attr(kind='medium')
    def test_d02_313(self):
        """show_port_attachment_port_not_found"""
        self._test_show_port_attachment(430)


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
                FakeQuantumProcess(self.config.nova.tenant_name))

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
                          '--project_id=%s '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 ' % self.config.nova.tenant_name,
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)


class LibvirtRebootErrorTest(LibvirtFunctionalTest):

    def _reboot_server_with_fake_libvirt(self, monkey_module,
            fakepath, fake_patch_name, status='ERROR', pass_get_info=False):

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
        if pass_get_info:
            patches.append(('nova.virt.libvirt.connection',
                        'fake_libvirt.libvirt_con_get_info_patch'))
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath)
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        self.ss_client.reboot(server['id'], 'HARD')

        if status == 'ACTIVE':
            self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')
        else:
            # Wait for the server to become ERROR.BUILD
            self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    @attr(kind='medium')
    def test_d02_303(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'lookup-error',
                                    'fake_libvirt.libvirt_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_d02_304(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'lookup-error',
                            'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE')

    @attr(kind='medium')
    def test_d02_318(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'lookup-error',
                                'fake_libvirt.libvirt_patch', 'ACTIVE', True)

    @attr(kind='medium')
    def test_d02_319(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'lookup-error',
                    'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE', True)

    @attr(kind='medium')
    def test_d02_321(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virdomain-error',
                                'fake_libvirt.libvirt_patch')

    @attr(kind='medium')
    def test_d02_322(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virdomain-error',
                                'fake_libvirt.libvirt_patch_invalid_operation')

    @attr(kind='medium')
    def test_d02_324(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virdomain-error',
                                'fake_libvirt.libvirt_patch_undefine')

    @attr(kind='medium')
    def test_d02_325(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virdomain-error',
                    'fake_libvirt.libvirt_undefine_patch_invalid_operation')

    @attr(kind='medium')
    def test_d02_327(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-unplug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_329(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-unplug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_331(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.firewall',
                        'firewall-error', 'fake_iptables.unfilter_patch')

    @attr(kind='medium')
    def test_d02_332(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-plug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_333(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-plug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_334(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-plug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_335(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.vif',
                        'vif-plug-error', 'fake_libvirt_vif.vif_patch')

    @attr(kind='medium')
    def test_d02_337(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virconn-error',
                                'fake_libvirt.libvirt_definexml_patch')

    @attr(kind='medium')
    def test_d02_340(self):
        self._reboot_server_with_fake_libvirt('libvirt', 'virdomain-error',
                                'fake_libvirt.libvirt_create_patch')

    @attr(kind='medium')
    def test_d02_343(self):
        self._reboot_server_with_fake_libvirt('nova.virt.libvirt.firewall',
                        'firewall-error', 'fake_iptables.filter_patch')
