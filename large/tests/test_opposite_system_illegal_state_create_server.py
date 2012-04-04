import unittest2 as unittest
import utils
from nose.plugins.attrib import attr
from storm.common.utils.data_utils import rand_name
from storm import exceptions
from nova import test


class CreateServerTest(unittest.TestCase):

    def _create_server(self, name, vm_state=None):
        # create server
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        _, server = self.ss_client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6)
        if server['status'] == '202':
            server_id = server['id']
            if vm_state:
                # Wait for the server to become active
                self.ss_client.wait_for_server_status(server_id, vm_state)
        else:
            server_id = None

        return server['status'], server_id

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_get(self):

        """
        Stop DB before _get_instance()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-sceduling)
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_get(self):

        """
        Raise Exception in DB before _get_instance()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status::building-scheduling
            virsh:-
            instance dir:not exist
            Error:nova-api.log
        """
        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('scheduling', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_can_not_connect_to_glance_when_image_show(self):

        """
        Stop glance before image_service.show()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_glance_no_response_when_image_show(self):

        """
        glance is no response:image_service.show()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_type_get(self):

        """
        Stop DB before db.instance_type_get()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-sceduling)
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_type_get(self):

        """
        Raise Exception in DB before db.instance_type_get()
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status::building-scheduling
            virsh:-
            instance dir:not exist
            Error:nova-api.log
        """
        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('scheduling', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_update_networking(self):

        """
        Stop DB before db.instance_update(SCHEDULING -> NETWORKING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-sceduling)
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_update_networking(self):

        """
        Raise Exception in DB before db.instance_update(SCHEDULING -> NETWORKING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status::building-scheduling
            virsh:-
            instance dir:not exist
            Error:nova-api.log
        """
        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('0', utils.get_instance_deleted_in_db(
                                                    self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('scheduling', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_400_ports(self):

        """
        Quantum return BadRequest(400)
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_403_ports(self):

        """
        Quantum return Forbidden(403)
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))
    
    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_420_ports(self):

        """
        Quantum return NetworkNotFound(420)
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))
    
    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_431_ports(self):

        """
        Quantum return RequestedStateInvalid(431)
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_440_ports(self):

        """
        Quantum return AlreadyAttached(440)
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_no_response_ports(self):

        """
        Quantum is no response
        POST /tenants/{tenant-id}/networks/{network-id}/ports
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_403_attachment(self):

        """
        Quantum return Forbidden(403)
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_420_attachment(self):

        """
        Quantum return NetworkNotFound(420)
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_430_attachment(self):

        """
        Quantum return PortNotFound(430)
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_432_attachment(self):

        """
        Quantum return PortInUse(432)
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_return_440_attachment(self):

        """
        Quantum return AlreadyAttached(440)
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_no_response_attachment(self):

        """
        Quantum is no response
        PUT /tenants/{tenant-id}/networks/{network-id}/ports/{port-id}/attachment
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_merange_return_500_ip_allocations(self):

        """
        Melange return Error response(500)
        ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_merange_no_response_ip_allocations(self):

        """
        Melange is no response
        ipam%(tenant_scope)s/networks/%(network_id)s/interfaces/%(vif_id)s/ip_allocations
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_update_bdm(self):

        """
        Stop DB before db.instance_update(NETWORKING -> BLOCK_DEVICE_MAPPING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-networking)
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_update_bdm(self):

        """
        Raise Exception in db.instance_update(NETWORKING -> BLOCK_DEVICE_MAPPING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-networking
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('networking', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_update_spawing(self):

        """
        Stop DB before db.instance_update(BLOCK_DEVICE_MAPPING -> SPAWING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-block_device_mapping)
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_update_spawing(self):

        """
        Raise Exception in db.instance_update(BLOCK_DEVICE_MAPPING -> SPAWING)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-block_device_mapping
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('block_device_mapping', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ip_link_show_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        execute('ip', 'link', 'show', 'dev', device,check_exit_code=False)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ip_tuntap_add_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('ip', 'tuntap', 'add', dev, 'mode', 'tap',run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ip_link_set_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('ip', 'link', 'set', dev, 'up', run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ovs_vsctl_add_port_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        ovs-vsctl add-port
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_ovs_vsctl_add_port_no_response(self):

        """
        Command is not response
        ovs-vsctl add-port
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_mkdir_basepath_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('mkdir', '-p', basepath(suffix=''))
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_open_libvirt_xml_raise_io_error(self):

        """
        Command raise OSError
        open(basepath('libvirt.xml'), 'w')
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_open_console_log_raise_io_error(self):

        """
        Command raise OSError
        os.close(os.open(console_log, os.O_CREAT | os.O_WRONLY, 0660))
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_can_not_connect_to_glance_when_image_get_kernel(self):

        """
        Stop glance before image_service.get()
        => kernel
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_glance_no_response_when_image_get_kernel(self):

        """
        Glance is no responce:image_service.get()
        => kernel
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_image_not_exist_when_image_get_kernel(self):

        """
        kernel is not exists on Glance:image_service.get()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def est_can_not_connect_to_glance_when_image_get_ram(self):

        """
        Stop glance before image_service.get()
        => ramdisk
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_glance_no_response_when_image_get_ram(self):

        """
        Glance is no responce:image_service.get()
        => ramdisk
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_image_not_exist_when_image_get_ram(self):

        """
        ramdisk is not exists on Glance:image_service.get()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_can_not_connect_to_glance_when_image_get_root(self):

        """
        Stop glance before image_service.get()
        => rootdisk
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_glance_no_response_when_image_get_root(self):

        """
        Glance is no responce:image_service.get()
        => rootdisk
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_image_not_exist_when_image_get_root(self):

        """
        image_service.get(context, image_id, image_file)
        => not image
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:202
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_qemu_img_convert_raise_execution_error(self):

        """
        utils.execute('qemu-img', 'convert', '-O', 'raw',path_tmp, staged)
        => ProcessExecutionError
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:202
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_qemu_img_convert_no_response(self):

        """
        utils.execute('qemu-img', 'convert', '-O', 'raw',path_tmp, staged)
        => ProcessExecutionError
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:202
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))













    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_truncate_target_ephemeral_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('truncate', target, '-s', "%d%c" % (local_size, unit))
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_mkfs_f_ephemeral_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('truncate', target, '-s', "%d%c" % (local_size, unit))
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_functools_partial_ephemeral_raise_error(self):

        """
        Command raise Error
        functools.partial(self._create_ephemeral,fs_label='ephemeral%d' % eph['num'],os_type=inst.os_type)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_truncate_target_swap_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('truncate', target, '-s', "%d%c" % (local_size, unit))
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_mkswap_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('mkswap', target)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_open_injected_nw_raise_io_error(self):

        """
        Command raise IOError
        open(FLAGS.injected_network_template).read()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_tune2fs_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('tune2fs', '-c', 0, '-i', 0,mapped_device, run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_mount_mapped_device_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        utils.execute('mount', mapped_device, tmpdir,run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_tee_a_keyfile_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
         utils.execute('mkdir', '-p', sshdir, run_as_root=True)
         utils.execute('chown', 'root', sshdir, run_as_root=True)
         utils.execute('chmod', '700', sshdir, run_as_root=True)
         keyfile = os.path.join(sshdir, 'authorized_keys')
         utils.execute('tee', '-a', keyfile, process_input='\n' + key.strip() + '\n', run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_tee_a_netfile_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
         utils.execute('mkdir', '-p', sshdir, run_as_root=True)
         utils.execute('chown', 'root', sshdir, run_as_root=True)
         utils.execute('chmod', '700', sshdir, run_as_root=True)
         keyfile = os.path.join(sshdir, 'authorized_keys')
         utils.execute('tee', '-a', keyfile, process_input='\n' + key.strip() + '\n', run_as_root=True)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_define_xml_raise_libvirt_error(self):

        """
        Raise LibvirtError on _conn.defineXML(xml)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_define_xml(self):

        """
        Stop libvirtd _conn.defineXML(xml)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_no_response_when_define_xml(self):

        """
        libvirtd is no response on _conn.defineXML(xml)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_create_with_flags_raise_libvirt_error(self):

        """
        Raise LibvirtError on domain.createWithFlags(launch_flags)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_create_with_flags(self):

        """
        Stop libvirtd domain.createWithFlags(launch_flags)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_no_response_when_create_with_flags(self):

        """
        libvirtd is no response on domain.createWithFlags(launch_flags)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_cmd_save_raise_execution_error(self):

        """
        Command raise ProcessExecutionError
        execute('%s-save' % (cmd,),'-t', '%s' % (table,),run_as_root=True,attempts=5)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_look_by_name_raise_libvirt_error(self):

        """
        Raise LibvirtError on _conn.lookupByName(instance_name)
        in _wait_for_boot()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_look_by_name_raise_vir_err_no_domain(self):

        """
        Raise VIR_ERR_NO_DOMAIN on _conn.lookupByName(instance_name)
        in _wait_for_boot()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:running
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertTrue(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_stopped_when_look_by_name(self):

        """
        Stop libvirtd on _conn.lookupByName(instance_name)
        in _wait_for_boot()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_libvirt_no_response_when_look_by_name(self):

        """
        libvirtd is no response on _conn.defineXML(xml)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName,'ERROR')

        """ assert
            response:204
            status::error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('NULL', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_stopped_when_instance_update_none(self):

        """
        Stop DB before db.instance_update(SPAWNING -> NONE)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:unknown(building-spawning)
            virsh:running
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_except_when_instance_update_none(self):

        """
        Raise Exception in db.instance_update(SPAWNING -> NONE)
        on ComputeManager._run_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-spawning
            virsh:running
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('spawning', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))
        self.assertEqual('running', utils.get_vm_state_in_virsh(server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_glance_is_stopped(self):

        """
        Stop Glance 
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:400
            Error:nova-api.log
        """

        # response
        self.assertEquals('400', resp)

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_immediately_after_stop_nova_cpu(self):

        """
        as soon as stop nova-compute,create server
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-scheduling
            virsh:-
            instance dir:not exist
            Error:Nothing
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('scheduling', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_1_minute_after_stop_nova_cpu(self):

        """
        stop nova-compute,create server after while
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-scheduler.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_rabbitmq_is_stopped(self):

        """
        stop RabbitMQ when scheduler select nova-compute
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-scheduler.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_id_has_been_granted(self):

        """
        Instance ID is used by the VM had been already
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_network_is_disconnected_when_download_image(self):

        """
        while downloading the image, network with Glance is disconnected
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertTrue(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_is_stopped(self):

        """
        creating a server, Quantum has been stopped
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_quantum_no_response(self):

        """
        creating a server, Quantum no response
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nvp_is_stopped(self):

        """
        creating a server, NVP has been stopped
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_db_is_stopped(self):

        """
        creating a server, DB has been stopped
        """

        # create server
        resp, _ = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('500', resp)

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_bdm_fail_when_nova_cpu_is_stopped(self):

        """
        creating a server, nova-compute has been stopped
        after instance_update(vm:BUILDING，task:BLOCK_DEVICE_MAPPING)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-block_device_mapping
            virsh:-
            instance dir:not exist
            Error:None
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('block_device_mapping', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_networking_fail_when_nova_cpu_is_stopped(self):

        """
        creating a server, nova-compute has been stopped
        after instance_update(vm:BUILDING，task:NETWORKING)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-networking
            virsh:-
            instance dir:not exist
            Error:None
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('networking', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_rabbitmq_is_stopped_when_ip(self):

        """
        creating a server, RabbitMQ has been stopped
        when nova-network.allocate_for_instance()
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:error-null
            virsh:-
            instance dir:not exist
            Error:nova-compute.log
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('error', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('Null', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))

    @test.skip_test('ignore this case')
    @attr(kind='large')
    def test_nova_cpu_is_stopped_when_update_instance(self):

        """
        creating a server, nova-compute has been stopped
        after instance_update(vm:BUILDING，task:SPAWNING)
        """

        # create server
        resp, server_id = self._create_server(self._testMethodName)

        """ assert
            response:202
            status:building-spawning
            virsh:-
            instance dir:not exist
            Error:None
        """

        # response
        self.assertEquals('202', resp)
        # db
        self.assertTrue(utils.exist_instance_in_db(self.config, server_id))
        self.assertEqual('building', utils.get_instance_vm_state_in_db(
                                                    self.config, server_id))
        self.assertEqual('spawning', utils.get_instance_task_state_in_db(
                                                    self.config, server_id))
        # virsh
        self.assertFalse(utils.exist_vm_in_virsh(server_id))
        self.assertFalse(utils.exist_instance_path(self.config,server_id))


