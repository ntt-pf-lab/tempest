import nose
from nose.plugins.attrib import attr
from tempest import openstack
from tempest import exceptions
from tempest import manager
from tempest.tests.compute.base import BaseComputeTest


class ServersTest(BaseComputeTest):

    @classmethod
    def setUpClass(cls):
        cls.wb_manager = manager.WhiteBoxManager()
        cls.wb_manager.connect_db()
        cls.client = cls.servers_client
        cls.img_client = cls.images_client

        cls.admin_username = cls.config.compute_admin.username
        cls.admin_password = cls.config.compute_admin.password
        cls.admin_tenant = cls.config.compute_admin.tenant_name

        if not(cls.admin_username and cls.admin_password and cls.admin_tenant):
            raise nose.SkipTest("Missing Admin credentials in configuration")
        cls.admin_os = openstack.AdminManager()
        cls.admin_client = cls.admin_os.admin_client

        # Get the tenant id needed for quota creation
        resp, tenants = cls.admin_client.list_tenants()
        cls.tenant_id = [tnt['id'] for tnt in tenants if tnt['name'] ==
                        cls.config.compute.tenant_name]

        # Get current number of servers in tenant
        resp, body = cls.client.list_servers()
        cls.num_of_servers = len(body['servers'])

    def tearDown(cls):
        for server in cls.servers:
            try:
                cls.client.delete_server(server['id'])
            except exceptions.NotFound:
                continue

    def update_state(self, server_id, vm_state, task_state, deleted=0):
        """Update states of an instance in database for validation"""
        if not task_state:
            task_state = 'NULL'

        sql = ("UPDATE instances SET "
               "deleted=%s, "
               "vm_state=%s, "
               "task_state=%s "
               "WHERE uuid=%s;")
        args = (deleted, vm_state, task_state, server_id)
        self.wb_manager.execute_query(sql, args)

    @attr(type='whitebox')
    def test_create_server_vcpu_quota_full(self):
        """Disallow server creation when tenant's vcpu quota is full"""
        sql = ("SELECT hard_limit from quotas "
               "WHERE project_id=%s AND "
               "resource='cores'")
        result = self.wb_manager.execute_query(sql, self.tenant_id,
                                               num_records='one')
        # Set vcpu quota for tenant if not already set
        if not result:
            cores_hard_limit = 2
            sql = ("INSERT INTO quotas "
                   "(deleted, project_id, resource, hard_limit) "
                   "VALUES(0, %s, 'cores', %s)")
            args = (self.tenant_id[0], cores_hard_limit)
            self.wb_manager.execute_query(sql, args)
        else:
            cores_hard_limit = result['hard_limit']

        try:
            # Create servers assuming 1 VCPU per instance i.e flavor_id=1
            for count in range(cores_hard_limit + 1):
                self.create_server()
                count = count + 1
        except exceptions.OverLimit:
            pass
        else:
            self.fail("Could create servers over the VCPU quota limit")
        finally:
            sql = ("DELETE from quotas")
            self.wb_manager.execute_query(sql)

    @attr(type='whitebox')
    def test_create_server_memory_quota_full(self):
        """Disallow server creation when tenant's memory quota is full"""
        sql = ("SELECT hard_limit from quotas "
               "WHERE project_id=%s AND "
               "resource='ram'")
        result = self.wb_manager.execute_query(sql, args=self.tenant_id,
                                               num_records='one')
        # Set memory quota for tenant if not already set
        if not result:
            ram_hard_limit = 1024
            sql = ("INSERT INTO quotas "
                   "(deleted, project_id, resource, hard_limit) "
                   "VALUES(0, %s, 'ram', %s)")
            args = (self.tenant_id[0], ram_hard_limit)
            self.wb_manager.execute_query(sql, args)
        else:
            ram_hard_limit = result['hard_limit']

        try:
            # Set a hard range of 3 servers for reaching the RAM quota
            for count in range(3):
                self.create_server()
        except exceptions.OverLimit:
            pass
        else:
            self.fail("Could create servers over the RAM quota limit")
        finally:
            sql = ("DELETE from quotas")
            self.wb_manager.execute_query(sql)

    def _test_delete_server_base(self, vm_state, task_state):
        """
        Base method for delete server tests based on vm and task states.
        Validates for successful server termination.
        """
        try:
            server = self.create_server()
            self.update_state(server['id'], vm_state, task_state)

            resp, body = self.client.delete_server(server['id'])
            self.assertEqual('204', resp['status'])
            self.client.wait_for_server_termination(server['id'],
                                                    ignore_error=True)

            sql = ("SELECT deleted, vm_state, task_state from instances "
                   "WHERE uuid=%s")

            result = self.wb_manager.execute_query(sql, args=server['id'],
                                                       num_records='one')
            self.assertEqual(1, result['deleted'])
            self.assertEqual('deleted', result['vm_state'])
            self.assertEqual(None, result['task_state'])
        except:
            self.fail("Should be able to delete a server when vm_state=%s and "
                      "task_state=%s" % (vm_state, task_state))

    def _test_delete_server_409_base(self, vm_state, task_state):
        """
        Base method for delete server tests based on vm and task states.
        Validates for 409 error code.
        """
        try:
            server = self.create_server()
            self.update_state(server['id'], vm_state, task_state)

            self.assertRaises(exceptions.Duplicate,
                              self.client.delete_server, server['id'])
        except:
            self.fail("Should not allow delete server when vm_state=%s and "
                    "task_state=%s" % (vm_state, task_state))
        finally:
            self.update_state(server['id'], 'active', None)

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_building_task_eq_networking(self):
        """Delete server when instance states are building,networking"""
        self._test_delete_server_base('building', 'networking')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_building_task_eq_bdm(self):
        """
        Delete server when instance states are building,block device mapping
        """
        self._test_delete_server_base('building', 'block_device_mapping')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_building_task_eq_spawning(self):
        """Delete server when instance states are building,spawning"""
        self._test_delete_server_base('building', 'spawning')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_active_task_eq_image_backup(self):
        """Delete server when instance states are active,image_backup"""
        self._test_delete_server_base('active', 'image_backup')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_active_task_eq_rebuilding(self):
        """Delete server when instance states are active,rebuilding"""
        self._test_delete_server_base('active', 'rebuilding')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_error_task_eq_building(self):
        """Delete server when instance states are error,building"""
        self._test_delete_server_base('error', 'building')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_prep(self):
        """Delete server when instance states are resizing,resize_prep"""
        self._test_delete_server_409_base('resizing', 'resize_prep')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_migrating(self):
        """Delete server when instance states are resizing,resize_migrating"""
        self._test_delete_server_409_base('resizing', 'resize_migrating')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_migrated(self):
        """Delete server when instance states are resizing,resize_migrated"""
        self._test_delete_server_409_base('resizing', 'resize_migrated')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_finish(self):
        """Delete server when instance states are resizing,resize_finish"""
        self._test_delete_server_409_base('resizing', 'resize_finish')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_reverting(self):
        """Delete server when instance states are resizing,resize_reverting"""
        self._test_delete_server_409_base('resizing', 'resize_reverting')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_resize_confirming(self):
        """Delete server when instance states are resizing,resize_confirming"""
        self._test_delete_server_409_base('resizing', 'resize_confirming')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_active_task_eq_resize_verify(self):
        """Delete server when instance states are active,resize_verify"""
        self._test_delete_server_base('active', 'resize_verify')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_active_task_eq_rebooting(self):
        """Delete server when instance states are active,rebooting"""
        self._test_delete_server_base('active', 'rebooting')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_building_task_eq_deleting(self):
        """Delete server when instance states are building,deleting"""
        self._test_delete_server_base('building', 'deleting')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_active_task_eq_deleting(self):
        """Delete server when instance states are active,deleting"""
        self._test_delete_server_base('active', 'deleting')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_error_task_eq_none(self):
        """Delete server when instance states are error,None"""
        self._test_delete_server_base('error', None)

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_migrating_task_eq_none(self):
        """Delete server when instance states are migrating,None"""
        self._test_delete_server_409_base('migrating', None)

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_resizing_task_eq_none(self):
        """Delete server when instance states are resizing,None"""
        self._test_delete_server_409_base('resizing', None)

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_error_task_eq_resize_prep(self):
        """Delete server when instance states are error,resize_prep"""
        self._test_delete_server_base('error', 'resize_prep')

    @attr(type='whitebox')
    def test_delete_server_when_vm_eq_error_task_eq_error(self):
        """Delete server when instance states are error,error"""
        self._test_delete_server_base('error', 'error')
