import os
import subprocess
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from tempest import openstack
import tempest.config
from tempest import exceptions
from tempest.common.utils.data_utils import rand_name
import stackmonkey.manager as ssh_manager

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess,
        FakeQuantumProcess)
from medium.tests.utils import (
        emphasised_print, silent_check_call,
        cleanup_virtual_instances, cleanup_processes)


config = tempest.config.TempestConfig('etc/medium-less-build_timeout.conf')
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # glance.
    environ_processes.append(GlanceRegistryProcess(
            config.images.source_dir,
            config.images.registry_config))
    environ_processes.append(GlanceApiProcess(
            config.images.source_dir,
            config.images.api_config,
            config.images.host,
            config.images.port))

    # keystone.
    environ_processes.append(KeystoneProcess(
            config.identity.source_dir,
            config.identity.config,
            config.identity.host,
            config.identity.port))

    for process in environ_processes:
        process.start()
    time.sleep(10)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class LibvirtFunctionalTest(unittest.TestCase):

    config = config

    def setUp(self):
        emphasised_print(self.id())

        self.havoc = ssh_manager.HavocManager()
        self.ssh_con = self.havoc.connect('127.0.0.1', 'openstack',
                        'openstack', self.havoc.config.nodes.ssh_timeout)

        self.glance_havoc = ssh_manager.GlanceHavoc(host='127.0.0.1',
            username='openstack', password='openstack',
            api_config_file=os.path.join(self.config.images.source_dir, self.config.images.api_config),
            registry_config_file=os.path.join(self.config.images.source_dir, self.config.images.registry_config))

        self.glance_ssh_con = self.glance_havoc.connect('127.0.0.1', 'openstack',
                            'openstack', self.glance_havoc.config.nodes.ssh_timeout)

        self.compute_havoc = ssh_manager.ComputeHavoc()
        self.compute_ssh_con = self.compute_havoc.connect('127.0.0.1', 'openstack',
                            'openstack', self.compute_havoc.config.nodes.ssh_timeout)

        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client
        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.compute.source_dir,
                self.config.compute.host,
                self.config.compute.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.compute.source_dir))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.compute.source_dir))

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
        silent_check_call('/opt/openstack/nova/bin/nova-manage db sync',
                          cwd=self.config.compute.source_dir, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        silent_check_call('/opt/openstack/nova/bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('/opt/openstack/nova/bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        # allocate networks.
        silent_check_call('/opt/openstack/nova/bin/nova-manage network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 ',
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)


    def get_nova_path(self, name):
        p = os.path.dirname(__file__)
        p = p.split(os.path.sep)[0:-2]
        return os.path.join(os.path.sep.join(p), name)


class LibvirtLaunchErrorTest(LibvirtFunctionalTest):
    @attr(kind='medium')
    def test_it(self):
        patches = [('libvirt', 'fake_libvirt.libvirt_patch')]
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path('launch-error') +\
            ':' + self.get_nova_path('stackmonkey')
        compute = NovaComputeProcess(self.config.compute.source_dir,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.compute.source_dir + '/bin/nova.conf')

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

        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')


class LibvirtLookupErrorTest(LibvirtFunctionalTest):
    @attr(kind='medium')
    def test_it(self):
        patches = [('libvirt', 'fake_libvirt.libvirt_patch')]
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path('lookup-error') +\
            ':' + self.get_nova_path('stackmonkey')
        compute = NovaComputeProcess(self.config.compute.source_dir,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.compute.source_dir + '/bin/nova.conf')

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

        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')


class LibvirtOpenVswitchDriverTest(LibvirtFunctionalTest):
    pass


class LibvirtOpenVswitchDriverPlugErrorTest(LibvirtOpenVswitchDriverTest):
    @attr(kind='medium')
    def test_it(self):
        patches = [('nova.virt.libvirt.vif', 'fake_libvirt_vif.vif_patch')]
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path('vif-plug-error') +\
            ':' + self.get_nova_path('stackmonkey')
        compute = NovaComputeProcess(self.config.compute.source_dir,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.compute.source_dir + '/bin/nova.conf')

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

        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')


class QuantumFunctionalTest(unittest.TestCase):

    config = config

    def setUp(self):
        emphasised_print(self.id())

        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.compute.source_dir,
                self.config.compute.host,
                self.config.compute.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.compute.source_dir))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.compute.source_dir))
        self.testing_processes.append(NovaComputeProcess(self.config.compute.source_dir,
                    config_file=self.config.compute.source_dir + '/bin/nova.conf'))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('/opt/openstack/nova/bin/nova-manage db sync',
                          cwd=self.config.compute.source_dir, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        self.os = openstack.Manager(config=self.config)
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

        # create users.
        silent_check_call('/opt/openstack/nova/bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('/opt/openstack/nova/bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def check_create_network(self, retcode):
        self.assertEqual(subprocess.call('/opt/openstack/nova/bin/nova-manage network create '
                                             '--label=private_1-1 '
                                             '--project_id=1 '
                                             '--fixed_range_v4=10.0.0.0/24 '
                                             '--bridge_interface=br-int '
                                             '--num_networks=1 '
                                             '--network_size=32 ',
                                         cwd=self.config.compute.source_dir,
                                         shell=True), retcode)

    def check_delete_network(self, retcode):
        self.assertEqual(subprocess.call('/opt/openstack/nova/bin/nova-manage network delete '
                                             '--network=10.0.0.0/24 ',
                                         cwd=self.config.compute.source_dir,
                                         shell=True), retcode)

    def _test_create_network(self, status_code):
        # quantum.
        quantum = FakeQuantumProcess('1', create_network=status_code)
        self.testing_processes.append(quantum)
        quantum.start()
        quantum.set_test(True)

        self.check_create_network(1)

    @attr(kind='medium')
    def test_create_network_bad_request(self):
        self._test_create_network(400)

    @attr(kind='medium')
    def test_create_network_forbidden(self):
        self._test_create_network(403)

    def _test_delete_network(self, status_code):
        # quantum.
        quantum = FakeQuantumProcess('1', delete_network=status_code)
        self.testing_processes.append(quantum)
        quantum.start()
        quantum.set_test(True)

        self.check_create_network(0)
        self.check_delete_network(1)

    @attr(kind='medium')
    def test_delete_network_bad_request(self):
        self._test_delete_network(400)

    @attr(kind='medium')
    def test_delete_network_forbidden(self):
        self._test_delete_network(403)

    @attr(kind='medium')
    def test_delete_network_network_not_found(self):
        self._test_delete_network(420)

    @attr(kind='medium')
    def test_delete_network_network_in_use(self):
        self._test_delete_network(421)

    def _execute_fake_and_wait_for_error(self, **param):
        # quantum.
        quantum = FakeQuantumProcess('1', **param)
        self.testing_processes.append(quantum)
        quantum.start()
        quantum.set_test(True)

        self.check_create_network(0)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6)

        # Wait for the server to become ERROR.BUILD
        self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    def _test_create_port(self, status_code):
        self._execute_fake_and_wait_for_error(create_port=status_code)

    @attr(kind='medium')
    def test_create_port_bad_request(self):
        self._test_create_port(400)

    @attr(kind='medium')
    def test_create_port_forbidden(self):
        self._test_create_port(403)

    @attr(kind='medium')
    def test_create_port_network_not_found(self):
        self._test_create_port(420)

    @attr(kind='medium')
    def test_create_port_requested_state_invalid(self):
        self._test_create_port(431)

    def _test_plug_port_attachment(self, status_code):
        self._execute_fake_and_wait_for_error(plug_port_attachment=status_code)

    @attr(kind='medium')
    def test_plug_port_attachment_forbidden(self):
        self._test_plug_port_attachment(403)

    @attr(kind='medium')
    def test_plug_port_attachment_network_not_found(self):
        self._test_plug_port_attachment(420)

    @attr(kind='medium')
    def test_plug_port_attachment_port_not_found(self):
        self._test_plug_port_attachment(430)

    @attr(kind='medium')
    def test_plug_port_attachment_port_in_use(self):
        self._test_plug_port_attachment(432)

    @attr(kind='medium')
    def test_plug_port_attachment_already_attached(self):
        self._test_plug_port_attachment(440)

    def _test_list_networks(self, status_code):
        self._execute_fake_and_wait_for_error(list_networks=status_code)

    @attr(kind='medium')
    def test_list_networks_forbidden(self):
        self._test_list_networks(403)

    def _test_list_ports(self, status_code):
        self._execute_fake_and_wait_for_error(list_ports=status_code)

    @attr(kind='medium')
    def test_list_ports_forbidden(self):
        self._test_list_ports(403)

    @attr(kind='medium')
    def test_list_ports_network_not_found(self):
        self._test_list_ports(420)

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
