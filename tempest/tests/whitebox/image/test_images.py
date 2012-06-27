from nose.plugins.attrib import attr

from tempest.common.utils.data_utils import rand_name
from tempest.tests.compute.base import BaseComputeTest
import tempest.config
from tempest import exceptions
from tempest import manager


class ImagesTest(BaseComputeTest):

    create_image_enabled = tempest.config.TempestConfig().\
            compute.create_image_enabled

    @classmethod
    def setUpClass(cls):
        cls.wb_manager = manager.WhiteBoxManager()
        cls.wb_manager.connect_db()
        cls.client = cls.images_client
        cls.servers_client = cls.servers_client
        cls.image_ids = []

    def tearDown(self):
        """Terminate test instances created after a test is executed"""

        for server in self.servers:
            self.update_state(server['id'], "active", None)
            resp, body = self.servers_client.delete_server(server['id'])
            if resp['status'] == '204':
                self.servers.remove(server)
                self.servers_client.wait_for_server_termination(server['id'])

        for image_id in self.image_ids:
            self.client.delete_image(image_id)
            self.image_ids.remove(image_id)

    def update_state(self, server_id, vm_state, task_state, deleted=0):
        """Update states of an instance in database for validation"""
        if not task_state:
            task_state = "NULL"

        sql = ("UPDATE instances SET "
              "deleted=%s, "
              "vm_state=%s, "
              "task_state=%s "
              "WHERE uuid=%s;")
        args = (deleted, vm_state, task_state, server_id)

        self.wb_manager.execute_query(sql, args)

    def _test_create_image_409_base(self, vm_state, task_state, deleted=0):
        """Base method for create image tests based on vm and task states"""
        try:
            server = self.create_server()
            self.update_state(server['id'], vm_state, task_state, deleted)
            image_name = rand_name('snap-')
            self.assertRaises(exceptions.Duplicate, self.client.create_image,
                              server['id'], image_name)
        except:
            self.fail("Should not allow create image when vm_state=%s and "
                      "task_state=%s" % (vm_state, task_state))
        finally:
            self.update_state(server['id'], 'active', None)

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_building_task_eq_scheduling(self):
        """409 error when instance states are building,scheduling"""
        self._test_create_image_409_base("building", "scheduling")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_building_task_eq_networking(self):
        """409 error when instance states are building,networking"""
        self._test_create_image_409_base("building", "networking")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_building_task_eq_bdm(self):
        """409 error when instance states are building,block_device_mapping"""
        self._test_create_image_409_base("building", "block_device_mapping")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_building_task_eq_spawning(self):
        """409 error when instance states are building,spawning"""
        self._test_create_image_409_base("building", "spawning")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_image_backup(self):
        """409 error when instance states are active,image_backup"""
        self._test_create_image_409_base("active", "image_backup")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_prep(self):
        """409 error when instance states are resizing,resize_prep"""
        self._test_create_image_409_base("resizing", "resize_prep")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_migrating(self):
        """409 error when instance states are resizing,resize_migrating"""
        self._test_create_image_409_base("resizing", "resize_migrating")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_migrated(self):
        """409 error when instance states are resizing,resize_migrated"""
        self._test_create_image_409_base("resizing", "resize_migrated")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_finish(self):
        """409 error when instance states are resizing,resize_finish"""
        self._test_create_image_409_base("resizing", "resize_finish")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_reverting(self):
        """409 error when instance states are resizing,resize_reverting"""
        self._test_create_image_409_base("resizing", "resize_reverting")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_resize_confirming(self):
        """409 error when instance states are resizing,resize_confirming"""
        self._test_create_image_409_base("resizing", "resize_confirming")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_resize_verify(self):
        """409 error when instance states are active,resize_verify"""
        self._test_create_image_409_base("active", "resize_verify")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_updating_password(self):
        """409 error when instance states are active,updating_password"""
        self._test_create_image_409_base("active", "updating_password")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_rebuilding(self):
        """409 error when instance states are active,rebuilding"""
        self._test_create_image_409_base("active", "rebuilding")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_rebooting(self):
        """409 error when instance states are active,rebooting"""
        self._test_create_image_409_base("active", "rebooting")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_building_task_eq_deleting(self):
        """409 error when instance states are building,deleting"""
        self._test_create_image_409_base("building", "deleting")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_active_task_eq_deleting(self):
        """409 error when instance states are active,deleting"""
        self._test_create_image_409_base("active", "deleting")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_error_task_eq_building(self):
        """409 error when instance states are error,building"""
        self._test_create_image_409_base("error", "building")

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_error_task_eq_none(self):
        """409 error when instance states are error,None"""
        self._test_create_image_409_base("error", None)

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_deleted_task_eq_none(self):
        """409 error when instance states are deleted,None"""
        self._test_create_image_409_base("deleted", None)

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_migrating_task_eq_none(self):
        """409 error when instance states are migrating,None"""
        self._test_create_image_409_base("migrating", None)

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_resizing_task_eq_none(self):
        """409 error when instance states are resizing,None"""
        self._test_create_image_409_base("resizing", None)

    @attr(type='whitebox')
    def test_create_image_when_vm_eq_error_task_eq_resize_prep(self):
        """409 error when instance states are error,resize_prep"""
