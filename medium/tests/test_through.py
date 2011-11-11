import subprocess
from nose.plugins.attrib import attr
from storm import openstack
from storm.common.utils.data_utils import rand_name
import base64
import storm.config
import unittest2 as unittest


class ServersTest(unittest.TestCase):

    config_path = 'etc/medium.config.ini'

    @classmethod
    def setUpClass(cls):
        # boot glance.

        cls.os = openstack.Manager()
        cls.client = cls.os.servers_client
        cls.config = storm.config.StormConfig(cls.config_path)
        cls.image_ref = cls.config.env.image_ref
        cls.flavor_ref = cls.config.env.flavor_ref
        cls.ssh_timeout = cls.config.nova.ssh_timeout

    @attr(type='smoke')
    def test_through(self):
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 meta=meta,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6,
                                                 personality=personality)

        #Wait for the server to become active
        self.client.wait_for_server_status(server['id'], 'ACTIVE')

        #Verify the specified attributes are set correctly
        resp, server = self.client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(self.image_ref, server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        #Teardown
        self.client.delete_server(self.id)
