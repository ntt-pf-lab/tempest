import os
import re
import subprocess
import tempfile
import time
import utils

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
import storm.config
from storm import exceptions
from storm.common.utils.data_utils import rand_name
from storm.services.keystone.json.keystone_client import TokenClient
import stackmonkey.manager as ssh_manager
from nova import test

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
from large.tests.utils import GlanceWrapper

config = storm.config.StormConfig('etc/large.conf')
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # keystone
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


class FunctionalTest(unittest.TestCase):

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

    def tearDown(self):
        self._dumpdb()

    def get_fake_path(self, name):
        return os.path.join(
                os.path.dirname(__file__),
                'fakes',
                name)

    def get_tests_path(self, name):
        p = os.path.dirname(__file__)
        p = p.split(os.path.sep)[0:-2]
        return os.path.join(os.path.sep.join(p), name)

    def mysql_start(self):
        try:
            for _ in range(5):
                self.havoc._run_cmd('sudo service mysql start')
                time.sleep(10)
                if self.havoc._run_cmd('sudo service mysql status'):
                    break
        except:
            pass

    def reset_db(self):
        silent_check_call('mysql -u%s -p%s -h%s -e "'
                          'DROP DATABASE IF EXISTS nova;'
                          'CREATE DATABASE nova;'
                          '"' % (
                              self.config.mysql.user,
                              self.config.mysql.password,
                              self.config.mysql.host),
                          shell=True)
        silent_check_call('bin/nova-manage db sync',
                          cwd=self.config.nova.directory, shell=True)

    def _dumpdb(self):
        subprocess.check_call('mysql -u%s -p%s -h%s -e "'
                              'connect nova;'
            'select id, event_type,publisher_id, status from eventlog;'
            'select id,vm_state,power_state,task_state,deleted from instances;'
            'select id, instance_id, network_id, address, deleted '
            'from virtual_interfaces;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)
        subprocess.check_call('mysql -u%s -p%s -h%s -e "'
                              'connect glance;'
                              'select id, status, deleted from images '
                              'order by created_at desc limit 1;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host),
                              shell=True)

    def assert_instance(self, server_id, status):
        if status == 'ACTIVE':
            self.assert_instance_active(server_id)
        elif status == 'ERROR':
            self.assert_instance_error(server_id)
        else:
            raise

    def assert_image(self, image_id, image_name, status):
        if status == 'active':
            self.assert_image_active(image_id, image_name)
        elif status == 'error':
            self.assert_image_error(image_id, image_name)
        elif status is None:
            self.assert_image_not_exist(image_id, image_name)
        else:
            raise

    def assert_instance_active(self, server_id):
        # assert virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        # assert db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # assert path
        self.assertTrue(utils.exist_instance_path(self.config, server_id))

    def assert_instance_error(self, server_id, vm_state='error',
                              task_state='NULL'):
        # assert virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        # assert db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual(vm_state, utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual(task_state, utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # assert path
        self.assertTrue(utils.exist_instance_path(self.config, server_id))

    def assert_image_active(self, image_id=None, image_name=None):
        if not image_name:
            image_id = utils.get_image_id_by_image_name_in_db(
                                                    self.config, image_name)
        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        self.assertEqual('0', utils.get_image_deleted_in_db(
                                                    self.config, image_id))
        self.assertEqual('active', utils.get_image_status_in_db(
                                                    self.config, image_id))
        # assert path
        self.assertTrue(utils.exist_image_path(self.config, image_id))

    def assert_image_error(self, image_id=None, image_name=None,
                           state='error'):
        if not image_name:
            image_id = utils.get_image_id_by_image_name_in_db(
                                                    self.config, image_name)
        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        self.assertEqual('1', utils.get_image_deleted_in_db(
                                                    self.config, image_id))
        self.assertEqual(state, utils.get_image_status_in_db(
                                                    self.config, image_id))
        # assert path
        self.assertFalse(utils.exist_image_path(self.config, image_id))

    def assert_image_not_exist(self, image_id=None, image_name=None):
        # assert db
        if not image_id:
            self.assertFalse(utils.exist_image_in_db(self.config, image_id))
        if not image_name:
            self.assertFalse(utils.exist_image_by_image_name_in_db(
                                                    self.config, image_name))
        # assert path
        self.assertFalse(utils.exist_image_path(self.config, image_id))


class GlanceErrorTest(FunctionalTest):

    config = config

    def setUp(self):
        super(GlanceErrorTest, self).setUp()

        # nova
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

        # glance
        self.testing_processes.append(GlanceRegistryProcess(
                self.config.glance.directory,
                self.config.glance.registry_config))

        # quantum
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db
        self.reset_db()

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)

        # allocate networks
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.nova.config,
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def tearDown(self):
        # start glance service
        glance_havoc = ssh_manager.GlanceHavoc()
        glance_havoc.start_glance_api()
        time.sleep(10)
        super(GlanceErrorTest, self).tearDown()

    def _create_image_with_fake_glance(self, monkey_module, fakepath,
                fake_patch_name, other_module_patchs, vm_status, image_status):

        # glance
        glance = GlanceApiProcess(self.config.glance.directory,
                                  self.config.glance.api_config,
                                  self.config.glance.host,
                                  self.config.glance.port)
        glance.start()
        self.testing_processes.append(glance)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        server_name = rand_name(self._testMethodName)
        _, server = self.ss_client.create_server(server_name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)
        server_id = server['id']
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        # replace glance by fake
        glance.stop()
        self.testing_processes.pop()
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            patches.append(other_module_patchs)
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath)
        glance = GlanceApiProcess(self.config.glance.directory,
                                  self.config.glance.api_config,
                                  self.config.glance.host,
                                  self.config.glance.port,
                                  patches=patches,
                                  env=env)
        glance.start()
        self.testing_processes.append(glance)
        time.sleep(10)

        # execute
        image_name = rand_name(self._testMethodName)
        self.ss_client.create_image(server_id, image_name)
        time.sleep(10)

        # assert
        self.assert_instance(server_id, vm_status)
        self.assert_image(None, image_name, image_status)

    def _create_image_when_ref_image_is_deleted(self, vm_status, image_status):
        """
        1. create server
        2. glance delete
        3. create image"
        """

        # glance
        self.testing_processes.append(GlanceRegistryProcess(
                self.config.glance.directory,
                self.config.glance.registry_config))
        self.testing_processes.append(GlanceApiProcess(
                self.config.glance.directory,
                self.config.glance.api_config,
                self.config.glance.host,
                self.config.glance.port))

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # glance add
        token_client = TokenClient(self.config)
        token = token_client.get_token(self.config.keystone.user,
                                       self.config.keystone.password,
                                       self.config.keystone.tenant_name)
        glance = GlanceWrapper(token, self.config)
        image_name = rand_name(self._testMethodName)
        image_file = os.path.abspath(tempfile.mkstemp()[1])
        #self.addCleanup(os.remove, image_file)
        image_id = glance.add(image_name, 'ari', 'ari', image_file)
        time.sleep(10)

        # create server
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        server_name = rand_name(self._testMethodName)
        _, server = self.ss_client.create_server(server_name,
                                                 image_id,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)
        server_id = server['id']
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        # glance delete
        glance.delete(image_id)
        time.sleep(10)

        # execute
        image_name = rand_name(self._testMethodName)
        self.ss_client.create_image(server_id, image_name)
        time.sleep(10)

        # assert
        self.assert_instance(server_id, vm_status)
        self.assert_image(None, image_name, image_status)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_401(self):
        """
        Cannot connect to Glance

        at nova.compute.api.py:API._create_image
            image_service.create(context, sent_meta)
        """
        #TODO
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', None)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_402(self):
        """
        No response from Glance

        at nova.compute.api.py:API._create_image
            image_service.create(context, sent_meta)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', None)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_423(self):
        """
        Cannot connect to Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.show(context, image_id)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_424(self):
        """
        No response from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.show(context, image_id)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_425(self):
        """
        NotFoundError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.show(context, image_id)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_433(self):
        """
        Cannot connect to Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.update(context, image_href, metadata, image_file)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_434(self):
        """
        No response from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.update(context, image_href, metadata, image_file)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_435(self):
        """
        NotFoundError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.update(context, image_href, metadata, image_file)
        """
        self._create_image_with_fake_glance('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_ci002(self):
        """
        Create image when the image referred by server is deleted
        """
        self._create_image_when_ref_image_is_deleted('ACTIVE', 'error')


class LibvirtErrorTest(FunctionalTest):

    config = config

    def setUp(self):
        super(LibvirtErrorTest, self).setUp()

        # nova
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        # glance
        self.testing_processes.append(GlanceRegistryProcess(
                self.config.glance.directory,
                self.config.glance.registry_config))
        self.testing_processes.append(GlanceApiProcess(
                self.config.glance.directory,
                self.config.glance.api_config,
                self.config.glance.host,
                self.config.glance.port))

        # quantum
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db
        self.reset_db()

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)
        # allocate networks
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.nova.config,
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def tearDown(self):
        self.havoc._run_cmd('sudo service mysql start')
        self.havoc._run_cmd('sudo service libvirt-bin start')
        super(LibvirtErrorTest, self).tearDown()

    def _create_image_with_fake_libvirt(self, monkey_module, fakepath,
            fake_patch_name, vm_status, image_status, pass_get_info=False):

        # nova-compute
        compute = NovaComputeProcess(self.config.nova.directory)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        server_name = rand_name(self._testMethodName)
        _, server = self.ss_client.create_server(server_name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)
        server_id = server['id']
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        # replace nova-compute by fake
        compute.stop()
        self.testing_processes.pop()
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

        # execute
        image_name = rand_name(self._testMethodName)
        self.ss_client.create_image(server_id, image_name)
        time.sleep(10)

        # assert
        self.assert_instance(server_id, vm_status)
        self.assert_image(None, image_name, image_status)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_405(self):
        """
        LibvirtError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # lookupByName is called in nova-compute start. What should I do?
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'lookup-error',
#                            'fake_libvirt.libvirt_patch', 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_406(self):
        """
        LibvirtError(VIR_ERR_NO_DOMAIN) from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # lookupByName is called in nova-compute start. What should I do?
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'lookup-error',
#                            'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_407(self):
        """
        Libvirt stopped

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # lookupByName is called in nova-compute start. What should I do?
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('nova.db.api',
#                            'create-image-error',
#                            'fake.instance_get_libvirt_stop_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_420(self):
        """
        LibvirtError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # replace lookupByName by fake when it is 2nd called
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'lookup-error',
#                                'fake_libvirt.libvirt_patch', 'ACTIVE', True)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_421(self):
        """
        LibvirtError(VIR_ERR_NO_DOMAIN) from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # replace lookupByName by fake when it is 2nd called
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'lookup-error',
#                    'fake_libvirt.libvirt_patch_no_domain', 'ACTIVE', True)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_422(self):
        """
        Libvirt stopped

        at nova.virt.libvirt.connection.py:LibvirtConnection._lookup_by_name
            _conn.lookupByName(instance_name)
        """
        #TODO
        # replace lookupByName by fake when it is 2nd called
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('nova.db.api',
#                'create-image-error',
#                'fake.virtual_interface_get_by_instance_libvirt_stop_patch',
#                'ACTIVE')

#    @attr(kind='large')
#    def test_d02_423(self):
#        self._snapshot_image_with_fake_libvirt('nova.image.glance',
#                'virconn-error', 'fake_libvirt.libvirt_glance_show_patch',
#                'ACTIVE')
#
#    @attr(kind='large')
#    def test_d02_425(self):
#        self._snapshot_image_with_fake_libvirt('nova.image.glance',
#                'virconn-error', 'fake_libvirt.libvirt_image_not_found_patch',
#                 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_426(self):
        """
        LibvirtError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            virt_dom.snapshotCreateXML(snapshot_xml, 0)
        """
        #TODO
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_427(self):
        """
        Libvirt stopped

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            virt_dom.snapshotCreateXML(snapshot_xml, 0)
        """
        #TODO
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'virdomain-error',
#                        'fake_libvirt.libvirt_snap_createxml_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_428(self):
        """
        LibvirtError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            virt_dom.XMLDesc(0)
        """
        #TODO
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'virdomain-error',
#                         'fake_libvirt.libvirt_snap_xmldesc_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_429(self):
        """
        Libvirt stopped

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            virt_dom.XMLDesc(0)
        """
        #TODO
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_430(self):
        """
        IOError

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            tempfile.mkdtemp()
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('tempfile',
#                        'general-error', 'fake.mkdtemp_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_431(self):
        """
        No response from command

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            utils.execute(*qemu_img_cmd)
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_432(self):
        """
        ProcessExecutionError from command

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            utils.execute(*qemu_img_cmd)
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('nova.utils',
#                        'general-error', 'fake.execute_patch', 'ACTIVE')

#    @attr(kind='large')
#    def test_d02_433(self):
#        self._snapshot_image_with_libvirt_error('nova.image.glance',
#                'virconn-error', 'fake_libvirt.libvirt_glance_update_patch',
#                'ACTIVE')
#
#    @attr(kind='large')
#    def test_d02_435(self):
#        self._snapshot_image_with_libvirt_error('nova.image.glance',
#                'virconn-error',
#                'fake_libvirt.libvirt_update_not_found_patch',
#                'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_436(self):
        """
        NotFoundError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            image_service.update(context,image_href,metadata,image_file)
        """
        self._create_image_with_fake_libvirt('', '', '', [],
                                             'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('shutil', 'general-error',
#                                               'fake.rmtree_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_437(self):
        """
        IOError

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            shutil.rmtree(temp_dir)
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('libvirt', 'virdomain-error',
#                    'fake_libvirt.libvirt_snap_delete_patch', 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_438(self):
        """
        LibvirtError from Glance

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            snapshot_ptr.delete(0)
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')
#        self._snapshot_image_with_libvirt_error('shutil', 'general-error',
#                                   'fake.shutil_rmtree_libvirt_stop_patch',
#                                   'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_439(self):
        """
        Libvirt stopped

        at nova.virt.libvirt.connection.py:LibvirtConnection.snapshot
            snapshot_ptr.delete(0)
        """
        self._create_image_with_fake_libvirt('', '', '', [], 'ACTIVE', 'error')


#class QuantumErrorTest(FunctionalTest):
#
#    config = config
#
#    def setUp(self):
#        super(QuantumErrorTest, self).setUp()
#
#        # nova
#        self.testing_processes.append(NovaApiProcess(
#                self.config.nova.directory,
#                self.config.nova.host,
#                self.config.nova.port))
#        self.testing_processes.append(NovaNetworkProcess(
#                self.config.nova.directory))
#        self.testing_processes.append(NovaSchedulerProcess(
#                self.config.nova.directory))
#        self.testing_processes.append(NovaComputeProcess(
#                self.config.nova.directory))
#
#        # glance
#        self.testing_processes.append(GlanceRegistryProcess(
#                self.config.glance.directory,
#                self.config.glance.registry_config))
#        self.testing_processes.append(GlanceApiProcess(
#                self.config.glance.directory,
#                self.config.glance.api_config,
#                self.config.glance.host,
#                self.config.glance.port))
#
#        # reset db
#        self.reset_db()
#
#        for process in self.testing_processes:
#            process.start()
#        time.sleep(10)
#
#        # create users
#        silent_check_call('bin/nova-manage user create '
#                          '--name=admin --access=secrete --secret=secrete',
#                          cwd=self.config.nova.directory, shell=True)
#        # create projects
#        silent_check_call('bin/nova-manage project create '
#                          '--project=1 --user=admin',
#                          cwd=self.config.nova.directory, shell=True)
#
#        self.addCleanup(cleanup_virtual_instances)
#        self.addCleanup(cleanup_processes, self.testing_processes)
#
#    def tearDown(self):
#        super(QuantumErrorTest, self).tearDown()
#
#    def check_create_network(self, retcode):
#        self.assertEqual(subprocess.call('bin/nova-manage '
#                                         '--flagfile=%s '
#                                         'network create '
#                                         '--label=private_1-1 '
#                                         '--project_id=1 '
#                                         '--fixed_range_v4=10.0.0.0/24 '
#                                         '--bridge_interface=br-int '
#                                         '--num_networks=1 '
#                                         '--network_size=32 '
#                                         % self.config.nova.config,
#                                         cwd=self.config.nova.directory,
#                                         shell=True), retcode)
#
#    def _create_image_with_quantum(self, vm_status, image_status, **param):
#        # quantum
#        quantum = QuantumProcess(self.config.quantum.directory,
#                        self.config.quantum.config)
#        quantum_plugin = QuantumPluginOvsAgentProcess(
#                        self.config.quantum.directory,
#                        self.config.quantum.agent_config)
#
#        self.testing_processes.append(quantum)
#        self.testing_processes.append(quantum_plugin)
#        quantum.start()
#        quantum_plugin.start()
#
#        self.check_create_network(0)
#
#        accessIPv4 = '1.1.1.1'
#        accessIPv6 = '::babe:220.12.22.2'
#        server_name = rand_name(self._testMethodName)
#        _, server = self.ss_client.create_server(server_name,
#                                                 self.image_ref,
#                                                 self.flavor_ref,
#                                                 accessIPv4=accessIPv4,
#                                                 accessIPv6=accessIPv6)
#        server_id = server['id']
#        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')
#
#        emphasised_print('Start testing %s' % self.id())
#
#        if param['delete_vif_db']:
#            subprocess.check_call('mysql -u%s -p%s -h%s -e "'
#                                  'connect nova;'
#                                  'delete from fixed_ips;'
#                                  'delete from virtual_interfaces;'
#                                  '"' % (
#                                      self.config.mysql.user,
#                                      self.config.mysql.password,
#                                      self.config.mysql.host),
#                                  shell=True)
#
#        # execute
#        image_name = rand_name(self._testMethodName)
#        self.ss_client.create_image(server_id, image_name)
#        time.sleep(10)
#
#        # assert
#        self.assert_instance(server_id, vm_status)
#        self.assert_image(None, image_name, image_status)
#
#    def _create_image_with_fake_quantum(self, vm_status, image_status,
#                                        **param):
#        # quantum
#        quantum = FakeQuantumProcess('1', **param)
#        self.testing_processes.append(quantum)
#        quantum.start()
#
#        self.check_create_network(0)
#
#        accessIPv4 = '1.1.1.1'
#        accessIPv6 = '::babe:220.12.22.2'
#        server_name = rand_name(self._testMethodName)
#        _, server = self.ss_client.create_server(server_name,
#                                                 self.image_ref,
#                                                 self.flavor_ref,
#                                                 accessIPv4=accessIPv4,
#                                                 accessIPv6=accessIPv6)
#        server_id = server['id']
#        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')
#
#        emphasised_print('Start testing %s' % self.id())
#        quantum.set_test(True)
#
#        # execute
#        image_name = rand_name(self._testMethodName)
#        self.ss_client.create_image(server_id, image_name)
#        time.sleep(10)
#
#        # assert
#        self.assert_instance(server_id, vm_status)
#        self.assert_image(None, image_name, image_status)
#
#    def _test_show_port_attachment(self, vm_status, image_status,
#                                   status_code):
#        self._create_image_with_fake_quantum(vm_status, image_status,
#                                         show_port_attachment=status_code)
#
#    @test.skip_test('Not yet implemented')
#    @attr(kind='large')
#    def test_d02_412(self):
#        self._create_image_with_quantum('ACTIVE', 'error', delete_vif_db=True)
#
#    @test.skip_test('Not yet implemented')
#    @attr(kind='large')
#    def test_d02_413(self):
#        """show_port_attachment_forbidden"""
#        self._test_show_port_attachment('ACTIVE', 'error', 403)
#
#    @test.skip_test('Not yet implemented')
#    @attr(kind='large')
#    def test_d02_414(self):
#        """show_port_attachment_network_not_found"""
#        self._test_show_port_attachment('ACTIVE', 'error', 420)
#
#    @test.skip_test('Not yet implemented')
#    @attr(kind='large')
#    def test_d02_415(self):
#        """show_port_attachment_port_not_found"""
#        self._test_show_port_attachment('ACTIVE', 'error', 430)


class DBErrorTest(FunctionalTest):

    config = config

    def setUp(self):
        super(DBErrorTest, self).setUp()

        # db start if stopped
        self.mysql_start()

        # nova
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

        # glance
        self.testing_processes.append(GlanceRegistryProcess(
                self.config.glance.directory,
                self.config.glance.registry_config))
        self.testing_processes.append(GlanceApiProcess(
                self.config.glance.directory,
                self.config.glance.api_config,
                self.config.glance.host,
                self.config.glance.port))

        # quantum
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db
        self.reset_db()

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)
        # allocate networks
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.nova.config,
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def tearDown(self):
        self.mysql_start()
        super(DBErrorTest, self).tearDown()

    def _create_image_with_fake_db(self, monkey_module, fakepath,
                fake_patch_name, other_module_patchs, vm_status, image_status):

        # nova-compute
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
        server_id = server['id']
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        # replace nova-compute by fake
        compute.stop()
        self.testing_processes.pop()
        patches = [(monkey_module, fake_patch_name)]
        if other_module_patchs:
            patches.append(other_module_patchs)
        env = os.environ.copy()
        env['PYTHONPATH'] = self.get_fake_path(fakepath) +\
            ':' + self.get_tests_path('stackmonkey')
        compute = NovaComputeProcess(self.config.nova.directory,
                                     patches=patches,
                                     env=env,
                                     config_file=self.config.nova.config)
        compute.start()
        self.testing_processes.append(compute)
        time.sleep(10)

        # execute
        image_name = rand_name(self._testMethodName)
        self.ss_client.create_image(server_id, image_name)
        time.sleep(10)

        # db start if stopped
        self.mysql_start()

        # assert
        self.assert_instance(server_id, vm_status)
        self.assert_image(None, image_name, image_status)

        self._dumpdb()

        # cleanup undeleted server
        self.ss_client.delete_server(server_id)
        subprocess.check_call('mysql -u%s -p%s -h%s -e "'
                              'connect nova;'
                              'update instances set deleted = 1, '
                              'vm_state = \'deleted\', task_state = null '
                              'where id = %s and deleted != 1 and '
                              'vm_state != \'deleted\' and '
                              'task_state is not null;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  self.config.mysql.host,
                                  server_id),
                              shell=True)

    @attr(kind='large')
    def test_d02_403(self):
        """
        DB stopped

        at nova.compute.api.py:API._create_image
            db.instance_get(context, instance_id)
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.db.api',
#                            'create-image-error', 'fake.db_stop_patch',
#                            [], 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_404(self):
        """
        SQLError from DB

        at nova.compute.api.py:API._create_image
            db.instance_get(context, instance_id)
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.db.api',
#                            'create-image-error', 'fake.db_exception_patch',
#                            [], 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_408(self):
        """
        DB stopped

        at nova.compute.manager.py:ComputeManager.snapshot_instance
            db.instance_update(context, instance_id, kwargs)

            when value of arg 'task_state' == IMAGE_SNAPSHOT
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.compute.manager',
#                    'create-image-error',
#                    'fake.instance_update_stop_patch_at_first_update',
#                    [], 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_409(self):
        """
        SQLError from DB

        at nova.compute.manager.py:ComputeManager.snapshot_instance
            db.instance_update(context, instance_id, kwargs)

            when value of arg 'task_state' == IMAGE_SNAPSHOT
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.compute.manager',
#                'create-image-error',
#                'fake.instance_update_except_patch_at_first_update',
#                [], 'ACTIVE')

#    @attr(kind='large')
#    def test_d02_410(self):
#        self._create_image_with_fake_db('nova.db.api',
#                'create-image-error',
#                'fake.virtual_interface_get_by_instance_stop_patch',
#                [], 'ACTIVE')
#
#    @attr(kind='large')
#    def test_d02_411(self):
#        self._create_image_with_fake_db('nova.db.api',
#                'create-image-error',
#                'fake.virtual_interface_get_by_instance_except_patch',
#                [], 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_440(self):
        """
        DB stopped

        at nova.compute.manager.py:ComputeManager.snapshot_instance
            db.instance_update(context, instance_id, kwargs)

            when value of arg 'task_state' is None
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.compute.manager',
#                    'create-image-error',
#                    'fake.instance_update_stop_patch_at_last_update',
#                    [], 'ACTIVE')

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_441(self):
        """
        SQLError from DB

        at nova.compute.manager.py:ComputeManager.snapshot_instance
            db.instance_update(context, instance_id, kwargs)

            when value of arg 'task_state' is None
        """
        self._create_image_with_fake_db('', '', '', [], 'ACTIVE', 'error')
#        self._create_image_with_fake_db('nova.compute.manager',
#                'create-image-error',
#                'fake.instance_update_except_patch_at_last_update',
#                [], 'ACTIVE')


class RabbitMQErrorTest(FunctionalTest):

    config = config

    def setUp(self):
        super(RabbitMQErrorTest, self).setUp()

        # nova
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

        # glance
        self.testing_processes.append(GlanceRegistryProcess(
                self.config.glance.directory,
                self.config.glance.registry_config))
        self.testing_processes.append(GlanceApiProcess(
                self.config.glance.directory,
                self.config.glance.api_config,
                self.config.glance.host,
                self.config.glance.port))

        # quantum
        self.testing_processes.append(FakeQuantumProcess('1'))

        # reset db
        self.reset_db()

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users
        silent_check_call('bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=self.config.nova.directory, shell=True)
        # create projects
        silent_check_call('bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=self.config.nova.directory, shell=True)

        # allocate networks
        silent_check_call('bin/nova-manage '
                          '--flagfile=%s '
                          'network create '
                          '--label=private_1-1 '
                          '--project_id=1 '
                          '--fixed_range_v4=10.0.0.0/24 '
                          '--bridge_interface=br-int '
                          '--num_networks=1 '
                          '--network_size=32 '
                          % self.config.nova.config,
                          cwd=self.config.nova.directory, shell=True)

        self.addCleanup(cleanup_virtual_instances)
        self.addCleanup(cleanup_processes, self.testing_processes)

    def tearDown(self):
        # start rabbitmq service
        try:
            self.havoc._run_cmd('sudo service rabbitmq-server start')
        except:
            pass
        super(RabbitMQErrorTest, self).tearDown()

    def _create_image_with_rabbitmq_stopped(self, monkey_module, fakepath,
                fake_patch_name, other_module_patchs, vm_status, image_status):

        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        server_name = rand_name(self._testMethodName)
        _, server = self.ss_client.create_server(server_name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)
        server_id = server['id']
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        # stop rabbitmq
        self.havoc._run_cmd('sudo service rabbitmq-server stop')
        time.sleep(10)

        # execute
        image_name = rand_name(self._testMethodName)
        self.ss_client.create_image(server_id, image_name)
        time.sleep(10)

        # assert
        self.assert_instance(server_id, vm_status)
        self.assert_image(None, image_name, image_status)

    @test.skip_test('Not yet implemented')
    @attr(kind='large')
    def test_d02_1401(self):
        """
        RabbitMQ stopped

        at nova.compute.api.py:API._cast_compute_message
            rpc.cast(context, queue, kwargs)
        """
        #TODO
        self._create_image_with_rabbitmq_stopped('', '', '', [],
                                                 'ACTIVE', 'error')
