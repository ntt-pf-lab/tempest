import unittest2 as unittest
from nose.plugins.attrib import attr
from tempest import exceptions
from tempest.tests.compute.base import BaseComputeTest


class VirtualInterfacesTest(BaseComputeTest):

    @classmethod
    def setUpClass(cls):
        cls.client = cls.servers_client
        cls.client.get_auth()
        cls.network_client = cls.os.network_client

    def tearDown(cls):
        for server in cls.servers:
            try:
                cls.client.delete_server(server['id'])
            except exceptions.NotFound:
                continue

    @attr(type='negative')
    def test_list_virtual_interfaces_valid_server_id(self):
        """List virtual interfaces of a valid server"""
        try:
            server = self.create_server()
            resp, body = self.client.list_server_virtual_interfaces(
                                                                  server['id'])
            self.assertEqual('200', resp['status'])
            vifs = body['virtual_interfaces']
            self.assertTrue(len(vifs) >= 1)
            self.assertIsNotNone(vifs[0]['id'])
            self.assertIsNotNone(vifs[0]['mac_address'])
        except:
            self.fail("Failed to list virtual interfaces of server")

    @attr(type='negative')
    @unittest.skip("Until Bug 1018831 is fixed")
    def test_list_virtual_interfaces_non_existent_server_id(self):
        """Fail an attempt to list virtual interfaces of non existent server"""
        self.assertRaises(exceptions.NotFound,
                         self.client.list_server_virtual_interfaces,
                        'abcd1234-abcd-1234-abcd-92843223s5123')

    @attr(type='negative')
    def test_virtual_interfaces_empty_server_id(self):
        """Fail an attempt to list virtual interfaces pass empty server id"""
        self.assertRaises(exceptions.NotFound,
                         self.client.list_server_virtual_interfaces, '')
