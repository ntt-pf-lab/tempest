import unittest2 as unittest
from nose.plugins.attrib import attr
from tempest import exceptions
from tempest import openstack
import tempest.config

config = tempest.config.TempestConfig()
username = config.identity.username
password = config.identity.password
tenant_name = config.identity.tenant_name


class FlavorsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Setup Client object for user with admin role
        cls.admin_os = openstack.Manager(username, password, tenant_name)
        cls.admin_client = cls.admin_os.flavors_client

        cls.os = openstack.Manager()
        cls.client = cls.os.flavors_client
        cls.config = cls.os.config
        cls.flavor_id = cls.config.compute.flavor_ref
        cls.flavor_name = 'test_flavor'
        cls.ram = 512
        cls.vcpus = 1
        cls.disk = 10
        cls.ephemeral = 10
        cls.new_flavor_id = 1234
        cls.swap = 1024
        cls.rxtx = 1

    @attr(type='smoke')
    def test_list_flavors(self):
        """List of all flavors should contain the expected flavor"""
        resp, flavors = self.client.list_flavors()
        resp, flavor = self.client.get_flavor_details(self.flavor_id)
        flavor_min_detail = {'id': flavor['id'], 'links': flavor['links'],
                             'name': flavor['name']}
        self.assertTrue(flavor_min_detail in flavors)

    @attr(type='smoke')
    def test_list_flavors_with_detail(self):
        """Detailed list of all flavors should contain the expected flavor"""
        resp, flavors = self.client.list_flavors_with_detail()
        resp, flavor = self.client.get_flavor_details(self.flavor_id)
        self.assertTrue(flavor in flavors)

    @attr(type='smoke')
    def test_get_flavor(self):
        """The expected flavor details should be returned"""
        resp, flavor = self.client.get_flavor_details(self.flavor_id)
        self.assertEqual(self.flavor_id, str(flavor['id']))

    @attr(type='negative')
    def test_get_non_existant_flavor(self):
        """flavor details are not returned for non existant flavors"""
        self.assertRaises(exceptions.NotFound, self.client.get_flavor_details,
                          999)

    @attr(type='positive', bug='lp912922')
    def test_list_flavors_limit_results(self):
        """Only the expected number of flavors should be returned"""
        params = {'limit': 1}
        resp, flavors = self.client.list_flavors(params)
        self.assertEqual(1, len(flavors))

    @attr(type='positive', bug='lp912922')
    def test_list_flavors_detailed_limit_results(self):
        """Only the expected number of flavors (detailed) should be returned"""
        params = {'limit': 1}
        resp, flavors = self.client.list_flavors_with_detail(params)
        self.assertEqual(1, len(flavors))

    @attr(type='positive')
    def test_list_flavors_using_marker(self):
        """The list of flavors should start from the provided marker"""
        resp, flavors = self.client.list_flavors()
        flavor_id = flavors[0]['id']

        params = {'marker': flavor_id}
        resp, flavors = self.client.list_flavors(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]),
                        'The list of flavors did not start after the marker.')

    @attr(type='positive')
    def test_list_flavors_detailed_using_marker(self):
        """The list of flavors should start from the provided marker"""
        resp, flavors = self.client.list_flavors_with_detail()
        flavor_id = flavors[0]['id']

        params = {'marker': flavor_id}
        resp, flavors = self.client.list_flavors_with_detail(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]),
                        'The list of flavors did not start after the marker.')

    @attr(type='positive')
    def test_list_flavors_detailed_filter_by_min_disk(self):
        """The detailed list of flavors should be filtered by disk space"""
        resp, flavors = self.client.list_flavors_with_detail()
        flavors = sorted(flavors, key=lambda k: k['disk'])
        flavor_id = flavors[0]['id']

        params = {'minDisk': flavors[1]['disk']}
        resp, flavors = self.client.list_flavors_with_detail(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]))

    @attr(type='positive')
    def test_list_flavors_detailed_filter_by_min_ram(self):
        """The detailed list of flavors should be filtered by RAM"""
        resp, flavors = self.client.list_flavors_with_detail()
        flavors = sorted(flavors, key=lambda k: k['ram'])
        flavor_id = flavors[0]['id']

        params = {'minRam': flavors[1]['ram']}
        resp, flavors = self.client.list_flavors_with_detail(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]))

    @attr(type='positive')
    def test_list_flavors_filter_by_min_disk(self):
        """The list of flavors should be filtered by disk space"""
        resp, flavors = self.client.list_flavors_with_detail()
        flavors = sorted(flavors, key=lambda k: k['disk'])
        flavor_id = flavors[0]['id']

        params = {'minDisk': flavors[1]['disk']}
        resp, flavors = self.client.list_flavors(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]))

    @attr(type='positive')
    def test_list_flavors_filter_by_min_ram(self):
        """The list of flavors should be filtered by RAM"""
        resp, flavors = self.client.list_flavors_with_detail()
        flavors = sorted(flavors, key=lambda k: k['ram'])
        flavor_id = flavors[0]['id']

        params = {'minRam': flavors[1]['ram']}
        resp, flavors = self.client.list_flavors(params)
        self.assertFalse(any([i for i in flavors if i['id'] == flavor_id]))

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
        self.assertEqual(flavor['id'], self.new_flavor_id)
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
            resp, _ = self.admin_client.create_flavor(flavor['name'], flavor['ram'],
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
            resp, _ = self.admin_client.create_flavor(flavor['name'], flavor['ram'],
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
        self.assertRaises(exceptions.NotFound, self.admin_client.get_flavor_details,
                            2000)

    def test_get_flavor_details_for_invalid_flavor_id(self):
        """ Return error because way to specify is inappropriate """

        self.assertRaises(exceptions.NotFound, self.client.get_flavor_details,
                        9999)





