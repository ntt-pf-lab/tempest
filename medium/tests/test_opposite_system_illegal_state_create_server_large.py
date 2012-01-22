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

    # nova.
    environ_processes.append(NovaApiProcess(
            config.nova.directory,
            config.nova.host,
            config.nova.port))
    environ_processes.append(NovaNetworkProcess(
            config.nova.directory))
    environ_processes.append(NovaSchedulerProcess(
            config.nova.directory))

    # quantum.
    environ_processes.append(
            FakeQuantumProcess('1'))

    # reset db.
    silent_check_call('mysql -u%s -p%s -e "'
                      'DROP DATABASE IF EXISTS nova;'
                      'CREATE DATABASE nova;'
                      '"' % (
                          config.mysql.user,
                          config.mysql.password),
                      shell=True)
    silent_check_call('bin/nova-manage db sync',
                      cwd=config.nova.directory, shell=True)

    for process in environ_processes:
        process.start()
    time.sleep(10)

    # create users.
    silent_check_call('bin/nova-manage user create '
                      '--name=admin --access=secrete --secret=secrete',
                      cwd=config.nova.directory, shell=True)
    # create projects.
    silent_check_call('bin/nova-manage project create '
                      '--project=1 --user=admin',
                      cwd=config.nova.directory, shell=True)

    # allocate networks.
    silent_check_call('bin/nova-manage network create '
                      '--label=private_1-1 '
                      '--project_id=1 '
                      '--fixed_range_v4=10.0.0.0/24 '
                      '--bridge_interface=br-int '
                      '--num_networks=1 '
                      '--network_size=32 ',
                      cwd=config.nova.directory, shell=True)

#    self.addCleanup(cleanup_virtual_instances)
#    self.addCleanup(cleanup_processes, self.testing_processes)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class LibvirtFunctionalTest(unittest.TestCase):

    config = config

    def tearDown(self):
        try:
            self._dumpdb()
        except:
            pass

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

        self.havoc = ssh_manager.HavocManager()
        self.ssh_con = self.havoc.connect('127.0.0.1', 'openstack',
                        'openstack', self.havoc.config.nodes.ssh_timeout)

        self.glance_havoc = ssh_manager.GlanceHavoc(host='127.0.0.1',
            username='openstack', password='openstack',
            api_config_file=os.path.join(self.config.glance.directory, self.config.glance.api_config),
            registry_config_file=os.path.join(self.config.glance.directory, self.config.glance.registry_config))
            
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
#        self.testing_processes.append(NovaApiProcess(
#                self.config.nova.directory,
#                self.config.nova.host,
#                self.config.nova.port))
#        self.testing_processes.append(NovaNetworkProcess(
#                self.config.nova.directory))
#        self.testing_processes.append(NovaSchedulerProcess(
#                self.config.nova.directory))
#
#        # quantum.
#        self.testing_processes.append(
#                FakeQuantumProcess('1'))
#
#        # reset db.
#        silent_check_call('mysql -u%s -p%s -e "'
#                          'DROP DATABASE IF EXISTS nova;'
#                          'CREATE DATABASE nova;'
#                          '"' % (
#                              self.config.mysql.user,
#                              self.config.mysql.password),
#                          shell=True)
#        silent_check_call('bin/nova-manage db sync',
#                          cwd=self.config.nova.directory, shell=True)
#
#
#        for process in self.testing_processes:
#            process.start()
#        time.sleep(10)
#
#
#        # create users.
#        silent_check_call('bin/nova-manage user create '
#                          '--name=admin --access=secrete --secret=secrete',
#                          cwd=self.config.nova.directory, shell=True)
#        # create projects.
#        silent_check_call('bin/nova-manage project create '
#                          '--project=1 --user=admin',
#                          cwd=self.config.nova.directory, shell=True)
#
#        # allocate networks.
#        silent_check_call('bin/nova-manage network create '
#                          '--label=private_1-1 '
#                          '--project_id=1 '
#                          '--fixed_range_v4=10.0.0.0/24 '
#                          '--bridge_interface=br-int '
#                          '--num_networks=1 '
#                          '--network_size=32 ',
#                          cwd=self.config.nova.directory, shell=True)
#
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


class CreateErrorNoStopTest(LibvirtFunctionalTest):

    def _create_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs):

        base_dir = os.path.join(self.config.nova.directory, 'instances/*')
        self.havoc._run_cmd('sudo rm -fr ' + base_dir)
        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_nova_path('stackmonkey')
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

    @attr(kind='large')
    def test_d02_102(self):
        self.assertRaises(exceptions.TimeoutException,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.db_exception_patch', [])

    @attr(kind='large')
    def test_d02_109(self):
        self.assertRaises(exceptions.TimeoutException,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.instance_update_except_patch', [])

    @attr(kind='large')
    def test_d02_129(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_except_patch', [])

    @attr(kind='large')
    def test_d02_131(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_spawn_except_patch', [])

    @attr(kind='large')
    def test_d02_138(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.libvirt_create_image_ioerror_patch', [])

    @attr(kind='large')
    def test_d02_139(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.libvirt_create_image_console_ioerror_patch', [])

    @attr(kind='large')
    def test_d02_156(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.libvirt_create_image_ioerror_patch', [])

    @attr(kind='large')
    def test_d02_173(self):
        self.assertRaises(exceptions.TimeoutException,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_active_except_patch', [])


class CreateStopDBTest(LibvirtFunctionalTest):

    def tearDown(self):
        try:
            self.havoc._run_cmd("sudo service mysql start")
        except:
            pass
        try:
            self.havoc._run_cmd("sudo glance -A nova index")
        except:
            pass
        try:
            self.compute_havoc.stop_nova_compute()
        except Exception:
            pass
        time.sleep(10)
        super(CreateStopDBTest, self).tearDown()

    def _create_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ACTIVE'):

        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_nova_path('stackmonkey')
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
                          server['id'], status)

    @attr(kind='large')
    def test_d02_101(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.db_stop_patch', [])

    @attr(kind='large')
    def test_d02_106(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.db_type_stop_patch', [])

    @attr(kind='large')
    def test_d02_108(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.instance_update_stop_patch', [])

    @attr(kind='large')
    def test_d02_128(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_stop_patch', [])

    @attr(kind='large')
    def test_d02_130(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_spawn_stop_patch', [])

    @attr(kind='large')
    def test_d02_172(self):
        self.assertRaises(TypeError,
            self._create_server_with_fake_db, 'nova.compute.manager', 'create-error',
                           'fake_db.compute_instance_update_active_stop_patch', [])


class CreateStopGlanceTest(LibvirtFunctionalTest):

    def tearDown(self):
        try:
            self.glance_havoc.start_glance_api()
        except:
            pass
        try:
            self.compute_havoc.stop_nova_compute()
        except Exception:
            pass
        time.sleep(10)
        super(CreateStopGlanceTest, self).tearDown()

    def _create_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ACTIVE'):

        base_dir = os.path.join(self.config.nova.directory, 'instances/*')
        self.havoc._run_cmd('sudo rm -fr ' + base_dir)
        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_nova_path('stackmonkey')
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
                          server['id'], status)

    @attr(kind='large')
    def test_d02_103(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.db.api', 'create-error',
                           'fake_db.stop_glance_patch', [], status='ERROR')

    @attr(kind='large')
    def test_d02_140(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.images', 'create-error',
                           'fake_db.libvirt_fetch_image_kerneldisk_stop_glance_patch', [])

    @attr(kind='large')
    def test_d02_143(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.images', 'create-error',
                           'fake_db.libvirt_fetch_image_ramdisk_stop_glance_patch', [])
    
    @attr(kind='large')
    def test_d02_146(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.images', 'create-error',
                           'fake_db.libvirt_fetch_image_rootdisk_stop_glance_patch', [])


class CreateStopLibvirtTest(LibvirtFunctionalTest):

    def tearDown(self):
        try:
            self.havoc._run_cmd("sudo service libvirt-bin start")
        except:
            pass
        try:
            self.compute_havoc.stop_nova_compute()
        except Exception:
            pass
        time.sleep(10)
        super(CreateStopLibvirtTest, self).tearDown()

    def _create_server_with_fake_db(self, monkey_module,
            fakepath, fake_patch_name, other_module_patchs, status='ACTIVE'):

        # start fake nova-compute for libvirt error
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            # [(monkey_module, fake_patch_name)]
            patches.append(other_module_patchs)

        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_nova_path('stackmonkey')
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
                          server['id'], status)

    @attr(kind='large')
    def test_d02_162(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.create_domain_stop_libvirt_patch', [])

    @attr(kind='large')
    def test_d02_165(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.create_domain_withflags_stop_libvirt_patch', [])

    @attr(kind='large')
    def test_d02_170(self):
        self.assertRaises(exceptions.BuildErrorException,
            self._create_server_with_fake_db, 'nova.virt.libvirt.connection', 'create-error',
                           'fake_db.create_domain_lookup_stop_libvirt_patch', [])