import base64
import re
import time
import subprocess

import unittest2 as unittest
from nose.plugins.attrib import attr

from tempest import openstack
import tempest.config
from tempest.common.utils.data_utils import rand_name
from medium.tests.utils import emphasised_print

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = tempest.config.TempestConfig('etc/medium.conf')
config = default_config


def setUpModule(module):
    config = module.config

    try:
        # create users.
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage user create '
                          '--name=admin --access=secrete --secret=secrete',
                          cwd=config.compute.source_dir, shell=True)
        # create projects.
        subprocess.check_call('/opt/openstack/nova/bin/nova-manage project create '
                          '--project=1 --user=admin',
                          cwd=config.compute.source_dir, shell=True)

    except Exception:
        pass


def tearDownModule(module):
    pass


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []


class ServersTest(FunctionalTest):
    def setUp(self):
        super(ServersTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

    @attr(kind='smoke')
    def test_through(self):
        emphasised_print("creating server.")
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        # Verify the specified attributes are set correctly
        resp, server = self.ss_client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(str(self.image_ref), server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        emphasised_print("creating snapshot.")
        # Make snapshot of the instance.
        alt_name = rand_name('server')
        resp, _ = self.ss_client.create_image(server['id'], alt_name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        alt_img_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(alt_img_id, 'ACTIVE')
        time.sleep(10)

        emphasised_print("deleting server.")
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        emphasised_print("creating server from snapshot.")
        resp, server = self.ss_client.create_server(name,
                                                    alt_img_id,
                                                    self.flavor_ref,
                                                    meta=meta,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')

        emphasised_print("deleting server again.")
        # Delete the server
        self.ss_client.delete_server(server['id'])
        self.ss_client.wait_for_server_not_exists(server['id'])

        emphasised_print("deleting snapshot.")
        # Delete the snapshot
        self.img_client.delete_image(alt_img_id)
        self.img_client.wait_for_image_not_exists(alt_img_id)


class FlavorsTest(FunctionalTest):
    # Almost same as tempest.tests.test_flavors,
    # but extends MT environment behavior.

    def setUp(self):
        super(FlavorsTest, self).setUp()
        self.flavor_ref = self.config.env.flavor_ref
        self.client = self.os.flavors_client

    @attr(kind='smoke')
    def test_list_flavors(self):
        """ List of all flavors should contain the expected flavor """
        resp, body = self.client.list_flavors()
        flavors = body['flavors']

        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        flavor_min_detail = {'id': flavor['id'], 'links': flavor['links'],
                             'name': flavor['name']}
        self.assertTrue(flavor_min_detail in flavors)

    @attr(kind='smoke')
    def test_list_flavors_with_detail(self):
        """ Detailed list of all flavors should contain the expected flavor """
        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertTrue(flavor in flavors)

    @attr(kind='smoke')
    def test_get_flavor(self):
        """ The expected flavor details should be returned """
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertEqual(self.flavor_ref, flavor['id'])
