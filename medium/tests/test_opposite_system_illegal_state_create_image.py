import os
import subprocess
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from kong import tests
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
        QuantumProcess, QuantumPluginOvsAgentProcess,
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
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect glance;'
                              'select id, status, deleted from images '
                              'order by created_at desc limit 1;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

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
        self.testing_processes.append(NovaComputeProcess(
                self.config.compute.source_dir))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
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
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def check_create_network(self, retcode):
        self.assertEqual(subprocess.call('bin/nova-manage '
                                         '--flagfile=%s '
                                         'network create '
                                         '--label=private_1-1 '
                                         '--project_id=1 '
                                         '--fixed_range_v4=10.0.0.0/24 '
                                         '--bridge_interface=br-int '
                                         '--num_networks=1 '
                                         '--network_size=32 '
                                         % self.config.compute.config,
                                         cwd=self.config.compute.source_dir,
                                         shell=True), retcode)

    def _execute_and_wait_for_error(self, **param):
        # quantum.
        quantum = QuantumProcess(self.config.network.source_dir,
                        self.config.network.config)
        quantum_plugin = QuantumPluginOvsAgentProcess(
                        self.config.network.source_dir,
                        self.config.network.agent_config)

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

        self.ss_client.create_image(server['id'], 'test_image_name')
        # Wait for the server to become ERROR.DELETED
#        self.assertRaises(exceptions.BuildErrorException,
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

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

        self.ss_client.create_image(server['id'], 'test_image_name')
        # Wait for the server to become ERROR.DELETED
#        self.assertRaises(exceptions.BuildErrorException,
        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

    def _test_show_port_attachment(self, status_code):
        self._execute_fake_and_wait_for_error(show_port_attachment=status_code)

    @tests.skip_test("Skip this testcase. This will be tested in large test")
    @attr(kind='medium')
    def test_db_virtual_interface_get_by_instance_with_vif_not_found(self):
        self._execute_and_wait_for_error(delete_vif_db=True)

    @attr(kind='medium')
    def test_get_port_with_forbidden(self):
        """show_port_attachment_forbidden"""
        self._test_show_port_attachment(403)

    @attr(kind='medium')
    def test_get_port_with_network_not_found(self):
        """show_port_attachment_network_not_found"""
        self._test_show_port_attachment(420)

    @attr(kind='medium')
    def test_get_port_with_port_not_found(self):
        """show_port_attachment_port_not_found"""
        self._test_show_port_attachment(430)


class LibvirtFunctionalTest(unittest.TestCase):

    config = config

    def tearDown(self):
        try:
            self.havoc._run_cmd("sudo service mysql start")
        except:
            pass

        try:
            self.havoc._run_cmd("sudo service libvirt-bin start")
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
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect glance;'
                              'select id, status, deleted from images '
                              'order by created_at desc limit 1;'
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
        self.testing_processes.append(NovaApiProcess(
                self.config.compute.source_dir,
                self.config.compute.host,
                self.config.compute.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.compute.source_dir))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.compute.source_dir))

        # quantum.
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.compute.source_dir, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        # allocate networks.
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.compute.config,
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)


class LibvirtSnapshotErrorTest(LibvirtFunctionalTest):

    def _snapshot_image_with_fake_libvirt(self, monkey_module,
            fakepath, fake_patch_name, status='ERROR', pass_get_info=False):

        compute = NovaComputeProcess(
                self.config.compute.source_dir)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        print 'server_name=' + name
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
        compute = NovaComputeProcess(self.config.compute.source_dir,
                                     patches=patches,
                                     env=env)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        image_name = rand_name('image')
        print 'image_name=' + image_name
        self.ss_client.create_image(server['id'], image_name)

        if status == 'ACTIVE':
            self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')
        else:
            # Wait for the server to become ERROR.BUILD
            self.assertRaises(exceptions.BuildErrorException,
                          self.ss_client.wait_for_server_status,
                          server['id'], 'ERROR')

    @attr(kind='medium')
    def test_conn_lookup_by_name_with_libvirt_error(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'lookup-error',
                                    'fake_libvirt.libvirt_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_conn_lookup_by_name_with_vir_err_no_domain(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'lookup-error',
                            'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE')

    @attr(kind='medium')
    def test_conn_lookup_by_name_with_stopped_libvirt(self):
        self._snapshot_image_with_fake_libvirt('nova.db.api',
                            'create-image-error',
                            'fake.instance_get_libvirt_stop_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_conn_lookup_by_name_2nd_with_libvirt_error(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'lookup-error',
                                'fake_libvirt.libvirt_patch', 'ACTIVE', True)

    @attr(kind='medium')
    def test_conn_lookup_by_name_2nd_with_vir_err_no_domain(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'lookup-error',
                    'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE', True)

    @attr(kind='medium')
    def test_conn_lookup_by_name_2nd_with_stopped_libvirt(self):
        self._snapshot_image_with_fake_libvirt('nova.db.api',
                'create-image-error',
                'fake.virtual_interface_get_by_instance_libvirt_stop_patch',
                'ACTIVE')

    @attr(kind='medium')
    def test_image_service_show_with_no_connection_to_glance(self):
        self._snapshot_image_with_fake_libvirt('nova.image.glance',
                'virconn-error', 'fake_libvirt.libvirt_glance_show_patch',
                'ACTIVE')

    @attr(kind='medium')
    def test_image_service_show_with_image_not_found(self):
        self._snapshot_image_with_fake_libvirt('nova.image.glance',
                'virconn-error', 'fake_libvirt.libvirt_image_not_found_patch',
                 'ACTIVE')

    @attr(kind='medium')
    def test_virt_dom_snapshot_create_xml_with_libvirt_error(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'virdomain-error',
                        'fake_libvirt.libvirt_snap_createxml_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_virt_dom_xml_desc_with_libvirt_error(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'virdomain-error',
                         'fake_libvirt.libvirt_snap_xmldesc_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_tempfile_mkdtemp_with_io_error(self):
        self._snapshot_image_with_fake_libvirt('tempfile',
                        'general-error', 'fake.mkdtemp_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_utils_execute_qemu_img_cmd_with_process_execution_error(self):
        self._snapshot_image_with_fake_libvirt('nova.utils',
                        'general-error', 'fake.execute_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_image_service_update_with_no_connection_to_glance(self):
        self._snapshot_image_with_fake_libvirt('nova.image.glance',
                'virconn-error', 'fake_libvirt.libvirt_glance_update_patch',
                'ACTIVE')

    @attr(kind='medium')
    def test_image_service_update_with_image_not_found(self):
        self._snapshot_image_with_fake_libvirt('nova.image.glance',
                'virconn-error', 'fake_libvirt.libvirt_update_not_found_patch',
                'ACTIVE')

    @attr(kind='medium')
    def test_shutil_rmtree_with_io_error(self):
        self._snapshot_image_with_fake_libvirt('shutil', 'general-error',
                                               'fake.rmtree_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_snapshot_ptr_delete_with_libvirt_error(self):
        self._snapshot_image_with_fake_libvirt('libvirt', 'virdomain-error',
                    'fake_libvirt.libvirt_snap_delete_patch', 'ACTIVE')

    @attr(kind='medium')
    def test_snapshot_ptr_delete_with_stopped_libvirt(self):
        self._snapshot_image_with_fake_libvirt('shutil', 'general-error',
                                       'fake.shutil_rmtree_libvirt_stop_patch',
                                       'ACTIVE')


class GlanceErrorTest(unittest.TestCase):

    config = config

    def tearDown(self):
        self._dumpdb()
        for process in environ_processes[:]:
            if isinstance(process, GlanceApiProcess):
                process.start()
        time.sleep(10)

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect glance;'
                              'select id, status, deleted from images '
                              'order by created_at desc limit 1;'
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
                self.config.compute.source_dir,
                self.config.compute.host,
                self.config.compute.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.compute.source_dir))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.compute.source_dir))

        # quantum.
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db.
        silent_check_call('mysql -u%s -p%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.compute.source_dir, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        # allocate networks.
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.compute.config,
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)

    def _snapshot_with_glance_error(self, monkey_module,
            fakepath, fake_patch_name, status='ERROR', pass_get_info=False):

        compute = NovaComputeProcess(
                self.config.compute.source_dir)
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

        # stop glance service
        for process in environ_processes[:]:
            if isinstance(process, GlanceApiProcess):
                process.stop()
        time.sleep(10)

        self.ss_client.create_image(server['id'], 'test_snapshot_image_name')

        self.ss_client.wait_for_server_status(
                          server['id'], 'ACTIVE')

    @attr(kind='medium')
    def test_image_service_create_with_no_connection_to_glance(self):
        self._snapshot_with_glance_error('', '', '')


class DBErrorTest(unittest.TestCase):

    config = config

    def tearDown(self):
        try:
            #self.havoc._run_cmd("sudo service mysql start")
            #time.sleep(10)
            for _ in range(0, 5):
                self.havoc._run_cmd("sudo service mysql start")
                time.sleep(10)
                if self.havoc._run_cmd("sudo service mysql status"):
                    break
        except:
            pass
        #self._dumpdb()

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
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect glance;'
                              'select id, status, deleted from images '
                              'order by created_at desc limit 1;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    def setUp(self):
        emphasised_print(self.id())

        self.havoc = ssh_manager.HavocManager()
        self.ssh_con = self.havoc.connect('127.0.0.1', 'openstack',
                        'openstack', self.havoc.config.nodes.ssh_timeout)

        self.mysql_start()

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
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.compute.source_dir, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.compute.source_dir, shell=True)
        # create projects.
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.compute.source_dir, shell=True)

        # allocate networks.
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.compute.config,
                          cwd=self.config.compute.source_dir, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)

    #def get_tests_path(self, name):
    #    p = os.path.dirname(__file__)
    #    p = p.split(os.path.sep)[0:-2]
    #    return os.path.join(os.path.sep.join(p), name)

    def mysql_start(self):
        try:
            for _ in range(0, 5):
                self.havoc._run_cmd("sudo service mysql start")
                time.sleep(10)
                if self.havoc._run_cmd("sudo service mysql status"):
                    break
        except:
            pass

    def _create_image_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ERROR'):

        compute = NovaComputeProcess(self.config.compute.source_dir)
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

        # start fake nova-compute for db error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath)
        #env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
        #    ':' + self.get_tests_path('stackmonkey')
        compute = NovaComputeProcess(self.config.compute.source_dir,
                                     patches=patches,
                                     env=env,
                    config_file=self.config.compute.source_dir + '/bin/nova.conf')

        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        # execute
        image_name = rand_name('image')
        print 'image_name=' + image_name
        resp, _ = self.ss_client.create_image(server['id'], image_name)
        #alt_img_url = resp['location']
        #match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        #self.assertIsNotNone(match)
        #image_id = match.groupdict()['image_id']
        time.sleep(10)

        # assert
        self.mysql_start()
        resp, server = self.ss_client.get_server(server['id'])
        print 'resp(ss_client.get_server)=' + str(resp)
        print 'body(ss_client.get_server)=' + str(server)
        self.assertEqual(status, server['status'])

        #resp, image = self.img_client.get_image(image_id)
        #print 'resp(img_client.get_image)=' + str(resp)
        #print 'body(img_client.get_image)=' + str(image)
        #self.assertEqual('404', resp['status'])

        self._dumpdb()

        # cleanup undeleted server
        self.ss_client.delete_server(server['id'])
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'connect nova;'
                              'update instances set deleted = 1, '
                              'vm_state = \'deleted\', task_state = null '
                              'where id = %s and deleted != 1 and '
                              'vm_state != \'deleted\' and '
                              'task_state is not null;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  server['id']),
                              shell=True)

    @attr(kind='medium')
    def test_db_instance_get_from_queue_with_stopped_db(self):
        self._create_image_with_fake_db('nova.db.api',
                            'create-image-error', 'fake.db_stop_patch',
                            [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_instance_get_from_queue_with_sql_error(self):
        self._create_image_with_fake_db('nova.db.api',
                            'create-image-error', 'fake.db_exception_patch',
                            [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_instance_update_to_image_snapshot_with_stopped_db(self):
        self._create_image_with_fake_db('nova.compute.manager',
                    'create-image-error',
                    'fake.instance_update_stop_patch_at_first_update',
                    [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_instance_update_to_image_snapshot_with_sql_error(self):
        self._create_image_with_fake_db('nova.compute.manager',
                'create-image-error',
                'fake.instance_update_except_patch_at_first_update',
                [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_virtual_interface_get_by_instance_with_stopped_db(self):
        self._create_image_with_fake_db('nova.db.api',
                'create-image-error',
                'fake.virtual_interface_get_by_instance_stop_patch',
                [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_virtual_interface_get_by_instance_with_sql_error(self):
        self._create_image_with_fake_db('nova.db.api',
                'create-image-error',
                'fake.virtual_interface_get_by_instance_except_patch',
                [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_instance_update_to_none_with_stopped_db(self):
        self._create_image_with_fake_db('nova.compute.manager',
                    'create-image-error',
                    'fake.instance_update_stop_patch_at_last_update',
                    [], 'ACTIVE')

    @attr(kind='medium')
    def test_db_instance_update_to_none_with_sql_error(self):
        self._create_image_with_fake_db('nova.compute.manager',
                'create-image-error',
                'fake.instance_update_except_patch_at_last_update',
                [], 'ACTIVE')
