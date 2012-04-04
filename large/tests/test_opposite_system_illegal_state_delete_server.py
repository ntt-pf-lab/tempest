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
    def test_db_stopped_when_instance_get(self):

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
            virsh:running
            instance dir:exist
            Error:nova-api.log
        """
        self.assertEqual('204', resp['status'])

        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_get(self):

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
        self.assertEquals('1', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_virtual_interface_get_by_instance(self):

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
            virsh:running
            instance dir:exist
            Error:nova-compute.log,nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_virtual_interface_get_by_instance(self):

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
        self.assertEqual('1', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_vif_not_found_when_virtual_interface_get_by_instance(self):

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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_403_when_get_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(403)
        GET /tenants/{tenant-id}/networks/{network-id}/
            ports/ {port-id}/attachment
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::deleting-active
            virsh:running
            instance dir:exist
            Error:nova-compute.log, nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_420_when_get_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(420)
        GET /tenants/{tenant-id}/networks/{network-id}/
            ports/ {port-id}/attachment
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::deleting-active
            virsh:running
            instance dir:exist
            Error:nova-compute.log, nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_430_when_get_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(430)
        GET /tenants/{tenant-id}/networks/{network-id}/
            ports/ {port-id}/attachment
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::deleting-active
            virsh:running
            instance dir:exist
            Error:nova-compute.log, nova-network.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('1', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_return_500_when_get_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(500)
        GET ipam%(tenant_scope)s/ip_blocks % locals()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-NULL
            virsh:-
            instance dir:exist
            Error:nova-compute.log, nova-network.log
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
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_no_response_when_get_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange is no response
        GET ipam%(tenant_scope)s/ip_blocks % locals()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status::error-NULL
            virsh:running
            instance dir:exist
            Error:nova-compute.log, nova-network.log
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
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_return_500_when_get_ip_allocations(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(500)
        GET ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/
        %(vif_id)s/ip_allocations % locals()
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_no_response_when_get_ip_allocations(self):

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
    def test_quantum_return_403_when_delete_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(403)
        DELETE /tenants/{tenant-id}/networks/
                {network-id}/ports/ {port-id}/attachment
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
    def test_quantum_return_420_when_delete_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(420)
        DELETE /tenants/{tenant-id}/networks/
                {network-id}/ports/ {port-id}/attachment
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
    def test_quantum_return_430_when_delete_attachment(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(430)
        DELETE /tenants/{tenant-id}/networks/
                {network-id}/ports/ {port-id}/attachment
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
    def test_quantum_return_400_when_delete_port(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(400)
        DELETE /tenants/{tenant-id}/networks/{network-id}/ports/ {port-id}
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
    def test_quantum_return_403_when_delete_port(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(403)
        DELETE /tenants/{tenant-id}/networks/{network-id}/ports/ {port-id}
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
        self.assertTrue(utils.exist_vif_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_420_when_delete_port(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(420)
        DELETE /tenants/{tenant-id}/networks/{network-id}/ports/ {port-id}
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
        self.assertTrue(utils.exist_vif_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_430_when_delete_port(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange returns Error(430)
        DELETE /tenants/{tenant-id}/networks/{network-id}/ports/ {port-id}
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
        self.assertTrue(utils.exist_vif_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_432_when_delete_port(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(432)
        DELETE ipam%(tenant_scope)s/networks/%(network_id)s/
        interfaces/%(vif_id)s/ip_allocations
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
    def test_melange_return_500_when_delete_ip_allocations(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange Return error response(500)
        DELETE ipam%(tenant_scope)s/networks/%(network_id)s/
        interfaces/%(vif_id)s/ip_allocations
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_no_response_when_delete_ip_allocations(self):
        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Melange is no response
        DELETE ipam%(tenant_scope)s/networks/%(network_id)s/
        interfaces/%(vif_id)s/ip_allocations
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_look_by_name_raise_libvirt_error(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Livbirt return LibvirtError
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_look_by_name_raise_vir_err_no_domain(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Livbirt return VIR_ERR_NO_DOMAIN
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_look_by_name(self):

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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_virt_dom_destroy_raise_libvirt_error(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Libvirt returns LibvirtError
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_virt_dom_destroy_raise_vir_err_no_domain(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Libvirt returns VIR_ERR_OPERATION_INVALID
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_virt_dom_destroy(self):

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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                        self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_virt_dom_undefine_raise_libvirt_error(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Libvirt return LibvirtError.
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('shut-off', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_virt_dom_undefine_raise_vir_err_no_domain(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Libvirt return VIR_ERR_OPERATION_INVALID.
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        self.assertFalse(utils.get_vif_instance_id_in_db(self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('shut-off', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_virt_dom_undefine(self):

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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('shut-off', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_del_port_raise_execution_error(self):

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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_del_port_no_response(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Execute command is no response
        virt/libvirt/vif.py
        LibvirtOpenVswitchDriver.unplug
        utils.execute('ovs-vsctl', 'del-port',FLAGS.libvirt_ovs_bridge, dev, run_as_root=True)
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:active-deleting
            virsh:-
            instance dir:non-exist
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ip_link_delete_raise_execution_error(self):

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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ip_link_delete_no_response(self):

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
            status:active-deleting
            virsh:-
            instance dir:non-exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('ACTIVE', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_del_ip_tables_raise_execution_error(self):

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
            status:deleted-NULL
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_shutil_rmtree_raise_io_error(self):

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
            status:deleted-none
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
        self.assertRaises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_update_deleting(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop DB before db.instance_update()
        on nova.compute.api.API.delete
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('202', resp['status'])

        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_update_deleting(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Raise Exception from DB BEFORE db.instance_update()
        on nova.compute.api.API.delete
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:active-null
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('202', resp['status'])

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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_destroy(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        STOP DB BEFORE db.instance_destroy()
        on nova.compute.api.API.delete
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:active-null
            instance dir:not exist
            Error:nova-compute.log
        """
        self.assertEqual('202', resp['status'])

        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('deleted', utils.get_vm_state_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_destroy(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Raise Exception from DB BEFORE db.instance_destroy()
        on nova.compute.api.API.delete
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:active-null
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('202', resp['status'])

        # db
        self.assertFalse(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('deleted', utils.get_vm_state_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_rabbitmq_is_stopped(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop RabbitMQ Process
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log, nova-network, nova-scheduler
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nova_cpu_is_stopped_when_update_instance_then_delete(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop nova-compute Process
        and delete server within a minute.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nova_cpu_is_stopped_when_update_instance(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop nova-compute Process
        and delete server after few minutes.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_melange_is_stopped(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop Melange Process
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log, nova-network
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_one_of_vifs_failed_to_delete(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Failure to delete one of VIFs
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log, nova-network
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_one_of_ports_failed_to_delete(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Quantum fails to delete port.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:error-NULL
            instance dir:not exist
            Error:nova-compute.log, nova-network
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertFalse(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertRises(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('deleted', utils.get_vm_state_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_dnsmasq_is_stopped(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop dnsmasq.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log, nova-network
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_stop_instruction_from_libvirt(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:1
            status:anyone-anyone
            instance dir:not exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertFalse(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('anyone', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('anyone', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertRaise(Exception, utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('deleted', utils.get_vm_state_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nvp_is_stopped(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop NVP Process.
        """

        # delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:not exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_lookup_by_name(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before _lookup_by_name()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """
        Restart libvirtd.
        """

        """ assert
            response:204
            deleted:1
            status:deleted-NULL
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_virt_dom_destroy_with_destroy(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before virt_dom.destroy()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """
        Restart libvirtd.
        """

        """ assert
            response:204
            deleted:1
            status:deleted-NULL
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
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_virt_dom_undefine_with_destroy(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop libvirtd before virt_dom.undefine()
        on LibvirtConnection.destroy()
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """
        Restart libvirtd.
        """
        """ assert
            response:204
            deleted:1
            status:deleted-NULL
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertFalse(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('1', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleted', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('shut-off', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nova_cpu_is_stopped_when_update_instance_then_delete_assert_reboot(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop nova-compute process.
        and delete server within a minute.
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nova_cpu_is_stopped_when_update_instance_assert_reboot(self):

        # create server
        server_id = self._create_server(self._testMethodName)

        """
        Stop nova-compute process.
        and delete after few minutes.
        """

        # Delete server
        resp, _ = self.ss_client.delete_server(server_id)

        """ assert
            response:204
            deleted:0
            status:active-deleting
            instance dir:exist
            Error:nova-compute.log
        """
        self.assertEqual('204', resp['status'])

        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('active', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('deleting', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_power_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('0', utils.get_instance_exist_fixed_ips_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))