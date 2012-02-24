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
    def test_D02_101(self):

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
    def test_D02_102(self):

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
    def test_D02_103(self):

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
    def test_D02_104(self):

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
    def test_D02_106(self):

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
    def test_D02_107(self):

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
    def test_D02_108(self):

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
    def test_D02_109(self):

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
    def test_D02_110(self):

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
    def test_D02_111(self):

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
    def test_D02_112(self):

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
    def test_D02_113(self):

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
    def test_D02_114(self):

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
    def test_D02_115(self):

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
    def test_D02_116(self):

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
    def test_D02_117(self):

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
    def test_D02_118(self):

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
    def test_D02_119(self):

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
    def test_D02_120(self):

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
    def test_D02_121(self):

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
    def test_D02_126(self):

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
    def test_D02_127(self):

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
    def test_D02_128(self):

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
    def test_D02_129(self):

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
    def test_D02_130(self):

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
    def test_D02_131(self):

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
    def test_D02_132(self):

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
    def test_D02_133(self):

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
    def test_D02_134(self):

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
    def test_D02_135(self):

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
    def test_D02_136(self):

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
    def test_D02_137(self):

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
    def test_D02_138(self):

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
    def test_D02_139(self):

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
    def test_D02_140(self):

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
    def test_D02_141(self):

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
    def test_D02_142(self):

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
    def test_D02_143(self):

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
    def test_D02_144(self):

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
    def test_D02_145(self):

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
    def test_D02_146(self):

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
    def test_D02_147(self):

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
    def test_D02_148(self):

        """
        root disk is not exists on Glance:image_service.get()
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
    def test_D02_151(self):

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
    def test_D02_152(self):

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
    def test_D02_153(self):

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
    def test_D02_154(self):

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
    def test_D02_155(self):

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
    def test_D02_156(self):

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
    def test_D02_157(self):

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
    def test_D02_158(self):

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
    def test_D02_159(self):

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
    def test_D02_160(self):

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
    def test_D02_161(self):

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
    def test_D02_162(self):

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
    def test_D02_163(self):

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
    def test_D02_164(self):

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
    def test_D02_165(self):

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
    def test_D02_166(self):

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
    def test_D02_167(self):

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
    def test_D02_168(self):

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
    def test_D02_169(self):

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
    def test_D02_170(self):

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
    def test_D02_171(self):

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
    def test_D02_172(self):

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
    def test_D02_173(self):

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
    def test_CS001(self):

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
    def test_CS002(self):

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
    def test_CS003(self):

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
    def test_CS004(self):

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
    def test_CS005(self):

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
    def test_CS006(self):

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
    def test_CS007(self):

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
    def test_CS009(self):

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
    def test_CS010(self):

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
    def test_CS011(self):

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
    def test_CS012(self):

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
    def test_CS013(self):

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
    def test_CS014(self):

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


