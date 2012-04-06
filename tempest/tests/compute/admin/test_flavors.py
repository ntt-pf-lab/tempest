import unittest2 as unittest
from nose.plugins.attrib import attr
from tempest import exceptions
from tempest import openstack


class FlavorsAdminTest(unittest.TestCase):

    """
    Tests Flavors API Create and Delete that require admin privileges
    """

    @classmethod
    def setUpClass(cls):
        # Setup Client object for user with admin role
        cls.admin_os = openstack.AdminManager()
        cls.admin_client = cls.admin_os.flavors_client

        cls.config = cls.admin_os.config
        cls.flavor_id = cls.config.compute.flavor_ref
        cls.flavor_name = 'test_flavor'
        cls.ram = 512
        cls.vcpus = 1
        cls.disk = 10
        cls.ephemeral = 10
        cls.new_flavor_id = 1234
        cls.swap = 1024
        cls.rxtx = 1

    @attr(type='positive')
    def test_create_flavor(self):
        """Test create flavor and newly created flavor is listed
        This operation requires the user to have 'admin' role"""

        #Create the flavor
        resp, flavor = self.admin_client.create_flavor(self.flavor_name,
                                                        self.ram, self.vcpus,
                                                        self.disk,
                                                        self.ephemeral,
                                                        self.new_flavor_id,
                                                        self.swap, self.rxtx)
        self.assertEqual(200, resp.status)
        self.assertEqual(flavor['name'], self.flavor_name)
        self.assertEqual(flavor['vcpus'], self.vcpus)
        self.assertEqual(flavor['disk'], self.disk)
        self.assertEqual(flavor['ram'], self.ram)
        self.assertEqual(int(flavor['id']), self.new_flavor_id)
        self.assertEqual(flavor['swap'], self.swap)
        self.assertEqual(flavor['rxtx_factor'], self.rxtx)
        self.assertEqual(flavor['OS-FLV-EXT-DATA:ephemeral'], self.ephemeral)

        #Verify flavor is retrieved
        resp, flavor = self.admin_client.get_flavor_details(self.new_flavor_id)
        self.assertEqual(resp.status, 200)
        self.assertEqual(flavor['name'], self.flavor_name)

        #Delete the flavor
        resp, body = self.admin_client.delete_flavor(flavor['id'])
        self.assertEqual(resp.status, 202)

    @attr(type='positive')
    def test_create_flavor_verify_entry_in_list_details(self):
        """Test create flavor and newly created flavor is listed in details
        This operation requires the user to have 'admin' role"""

        #Create the flavor
        resp, flavor = self.admin_client.create_flavor(self.flavor_name,
                                                        self.ram, self.vcpus,
                                                        self.disk,
                                                        self.ephemeral,
                                                        self.new_flavor_id,
                                                        self.swap, self.rxtx)
        flag = False
        #Verify flavor is retrieved
        resp, flavors = self.admin_client.list_flavors_with_detail()
        self.assertEqual(resp.status, 200)
        for flavor in flavors:
            if flavor['name'] == self.flavor_name:
                flag = True
        self.assertTrue(flag)

        #Delete the flavor
        resp, body = self.admin_client.delete_flavor(self.new_flavor_id)
        self.assertEqual(resp.status, 202)

    @attr(type='positive')
    def test_list_deleted_flavors(self):
        """List of all flavors should be blank"""

        # Backup list of flavors
        resp, flavors = self.admin_client.list_flavors_with_detail()
        orig_flavors = flavors

        # Delete all flavors
        for flavor in flavors:
            self.admin_client.delete_flavor(flavor['id'])

        resp, flavors = self.admin_client.list_flavors()
        self.assertEqual([], flavors)

        # Re create original flavors
        for flavor in orig_flavors:
            if not flavor['swap']:
                swap = 0
            else:
                swap = flavor['swap']
            resp, _ = self.admin_client.create_flavor(flavor['name'],
                                        flavor['ram'],
                                        flavor['vcpus'],
                                        flavor['disk'],
                                        flavor['OS-FLV-EXT-DATA:ephemeral'],
                                        flavor['id'], swap,
                                        int(flavor['rxtx_factor']))
            self.assertEqual(200, resp.status)

    @attr(type='positive')
    def test_list_flavor_details_when_all_flavors_deleted(self):
        """Detailed List of all flavors should be blank"""

        # Backup list of flavors
        resp, flavors = self.admin_client.list_flavors_with_detail()
        orig_flavors = flavors

        # Delete all flavors
        for flavor in flavors:
            self.admin_client.delete_flavor(flavor['id'])

        resp, flavors = self.admin_client.list_flavors_with_detail()
        self.assertEqual([], flavors)

        # Re create original flavors
        for flavor in orig_flavors:
            if not flavor['swap']:
                swap = 0
            else:
                swap = flavor['swap']
            resp, _ = self.admin_client.create_flavor(flavor['name'],
                                           flavor['ram'],
                                           flavor['vcpus'], flavor['disk'],
                                           flavor['OS-FLV-EXT-DATA:ephemeral'],
                                           flavor['id'], swap,
                                           int(flavor['rxtx_factor']))
            self.assertEqual(200, resp.status)

    @attr(type='negative')
    def test_get_flavor_details_raises_NotFound_for_deleted_flavor(self):
        """Return error because specified flavor is deleted"""

        # Create a test flavor
        resp, flavor = self.admin_client.create_flavor(self.flavor_name,
                                                self.ram,
                                                self.vcpus, self.disk,
                                                self.ephemeral, 2000,
                                                self.swap, self.rxtx)
        self.assertEquals(200, resp.status)

        # Delete the flavor
        resp, _ = self.admin_client.delete_flavor(2000)
        self.assertEqual(resp.status, 202)

        # Get deleted flavor details
        self.assertRaises(exceptions.NotFound,
                self.admin_client.get_flavor_details, 2000)
