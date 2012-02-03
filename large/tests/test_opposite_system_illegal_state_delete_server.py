import unittest2 as unittest
import utils
from nose.plugins.attrib import attr
from storm.common.utils.data_utils import rand_name
from storm import exceptions
from nova import test


class DeleteServerTest(unittest.TestCase):

    def _create_server(self,name):
        # create server
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        _, server = self.ss_client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)

        self.assertEquals('202', server['status'])
        server_id = server['id']

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server_id, 'ACTIVE')

        return server_id

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_201(self):

        # create server
        server_id = self._create_server(self._testMethodName)
        """
        Stop DB before _get_instance()
        on compute.api.API.delete()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::active-null
            virsh:running
            instance dir:exist
            Error:nova-api.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_202(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Raise Exception from DB before _get_instance()
        on compute.api.API.delete()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::active-null
            virsh:running
            instance dir:exist
            Error:nova-api.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_203(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop DB before db.virtual_interface_get_by_instance()
        on QuantumManager.get_instance_nw_info()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-null
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_204(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Raise Exception from DB before db.virtual_interface_get_by_instance()
        on QuantumManager.get_instance_nw_info()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_205(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Not exists VIF on DB before db.virtual_interface_get_by_instance()
        on QuantumManager.get_instance_nw_info()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:true
            status:deleted-none
            virsh:-
            instance dir:not exist
            Error:None
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_211(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(500)
        GET ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations % locals()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_212(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange is no response
        GET ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations % locals()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_220(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(500)
        DELETE ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_221(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange is no response
        DELETE ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_225(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before _lookup_by_name()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_228(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before virt_dom.destroy()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-none
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_231(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before virt_dom.undefine()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:shut-off
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('shut-off', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_232(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command raise ProcessExecutionError
        utils.execute('ovs-vsctl', 'del-port',FLAGS.libvirt_ovs_bridge, dev, run_as_root=True)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_233(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command is no response
        utils.execute('ovs-vsctl', 'del-port',FLAGS.libvirt_ovs_bridge, dev, run_as_root=True)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_234(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command raise ProcessExecutionError
        utils.execute('ip', 'link', 'delete', dev, run_as_root=True)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_235(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command is no response
        utils.execute('ip', 'link', 'delete', dev, run_as_root=True)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_236(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command raise ProcessExecutionError
        execute('%s-save' % (cmd,),'-t', '%s' % (table,),run_as_root=True,attempts=5)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_D02_237(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command raise IOError
        shutil.rmtree(target)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status::deleted-none
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

