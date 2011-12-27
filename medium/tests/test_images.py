# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 NTT
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import base64
import os
import re
import subprocess
import sys
import tempfile
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from kong import tests
from storm import openstack
import storm.config
from storm.services.nova.json.images_client import ImagesClient
from storm.services.nova.json.servers_client import ServersClient

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess)

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = storm.config.StormConfig('etc/medium.conf')
config = default_config
environ_processes = []


def setUpModule(module):
#    environ_processes = module.environ_processes
    config = module.config

    try:
        # reset db
        subprocess.check_call('mysql -u%s -p%s -D keystone -e "'
                              'DELETE FROM users WHERE name = \'user1\';'
                              'DELETE FROM users WHERE name = \'user2\';'
                              'DELETE FROM users WHERE name = \'user3\';'
                              'DELETE FROM tenants WHERE name = \'tenant1\';'
                              'DELETE FROM tenants WHERE name = \'tenant2\';'
                              'DELETE FROM user_roles WHERE NOT EXISTS '
                              '(SELECT * FROM users WHERE id = user_id);'
                              '"' % (
                                  config.mysql.user,
                                  config.mysql.password),
                              shell=True)

        # create tenants.
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage tenant add tenant1',
                              cwd=config.keystone.directory, shell=True)
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage tenant add tenant2',
                              cwd=config.keystone.directory, shell=True)

        # create users.
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage user add '
                              'user1 user1 tenant1',
                              cwd=config.keystone.directory, shell=True)
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage user add '
                              'user2 user2 tenant1',
                              cwd=config.keystone.directory, shell=True)
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage user add '
                              'user3 user3 tenant2',
                              cwd=config.keystone.directory, shell=True)

        # grant role
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage role grant '
                              'Member user1 tenant1',
                              cwd=config.keystone.directory, shell=True)
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage role grant '
                              'Member user2 tenant1',
                              cwd=config.keystone.directory, shell=True)
        subprocess.check_call('/opt/openstack/keystone/bin/keystone-manage role grant '
                              'Member user3 tenant2',
                              cwd=config.keystone.directory, shell=True)

    except Exception:
        pass


def tearDownModule(module):
    config = module.config

    # reset db
    try:
        subprocess.check_call('mysql -u%s -p%s -D keystone -e "'
                              'SELECT * FROM tenants;'
                              'SELECT users.id AS user_id, users.name AS '
                              'user_name, password, tenants.name AS '
                              'tenant_name, roles.name AS role_name FROM '
                              'user_roles, users, tenants, roles WHERE '
                              'user_roles.user_id = users.id AND '
                              'user_roles.tenant_id = tenants.id AND '
                              'user_roles.role_id = roles.id;'
                              'DELETE FROM users WHERE name = \'user1\';'
                              'DELETE FROM users WHERE name = \'user2\';'
                              'DELETE FROM users WHERE name = \'user3\';'
                              'DELETE FROM tenants WHERE name = \'tenant1\';'
                              'DELETE FROM tenants WHERE name = \'tenant2\';'
                              'DELETE FROM user_roles WHERE NOT EXISTS '
                              '(SELECT * FROM users WHERE id = user_id);'
                              '"' % (
                                  config.mysql.user,
                                  config.mysql.password),
                              shell=True)
    except Exception:
        pass


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

    def tearDown(self):
        # kill still existing virtual instances.
        print """

        Terminate All Instances

        """
        try:
            _, servers = self.os.servers_client.list_servers()
            print "Servers : %s" % servers
            for s in servers['servers']:
                try:
                    print "Find existing instance %s" % s['id']
                    resp, body = self.os.servers_client.delete_server(s['id'])
                    if resp['status'] == '200' or resp['status'] == '202':
                        self.os.servers_client.wait_for_server_not_exists(
                                                                    s['id'])
                        time.sleep(5)
                except Exception as e:
                    print e
        except Exception:
            pass
        print """

        Cleanup DB

        """
#        self.output_eventlog()


class ImagesTest(FunctionalTest):

    def setUp(self):
        super(ImagesTest, self).setUp()
        self.image_ref = self.config.env.image_ref
        self.flavor_ref = self.config.env.flavor_ref
        self.ss_client = self.os.servers_client
        self.img_client = self.os.images_client

        class config(object):
            class env(object):
                authentication = "keystone_v2"

            class nova(object):
                build_interval = self.config.nova.build_interval
                build_timeout = self.config.nova.build_timeout

        # user1
        user1 = {'username': 'user1', 'key': 'user1', 'tenant_name': 'tenant1',
                 'auth_url': self.config.nova.auth_url, 'config': config}
        self.ss_client_for_user1 = ServersClient(**user1)
        self.img_client_for_user1 = ImagesClient(**user1)
        # user2
        user2 = {'username': 'user2', 'key': 'user2', 'tenant_name': 'tenant1',
                 'auth_url': self.config.nova.auth_url, 'config': config}
        self.ss_client_for_user2 = ServersClient(**user2)
        self.img_client_for_user2 = ImagesClient(**user2)
        # user3
        user3 = {'username': 'user3', 'key': 'user3', 'tenant_name': 'tenant2',
                 'auth_url': self.config.nova.auth_url, 'config': config}
        self.ss_client_for_user3 = ServersClient(**user3)
        self.img_client_for_user3 = ImagesClient(**user3)

    def create_server(self):
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        time.sleep(5)

        # Wait for the server to become active
        self.ss_client.wait_for_server_status(server['id'], 'ACTIVE')
        self.server_id = server['id']

    @attr(kind='medium')
    def test_list_images_when_image_amount_is_zero(self):
        """ List of all images should contain the expected image """
        # make sure no record in db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images;'
                              'DELETE FROM images;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertEqual(0, len(images))

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_when_image_amount_is_one(self):
        """ List of all images should contain the expected image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # delete images for test
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images '
                              'WHERE id != %s;'
                              'DELETE FROM images WHERE id != %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(images))
        self.assertEqual(image_id, images[0]['id'])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_when_image_amount_is_three(self):
        """ List of all images should contain the expected image """
        # create a server for test
        self.create_server()

        # create an image for test
        image_ids = []
        for i in range(0, 3):
            name = 'server_' + self._testMethodName + '_' + str(i)
            resp, body = self.ss_client.create_image(self.server_id, name)
            alt_img_url = resp['location']
            match = re.search('/images/(?P<image_id>.+)', alt_img_url)
            self.assertIsNotNone(match)
            image_id = match.groupdict()['image_id']
            self.img_client.wait_for_image_status(image_id, 'ACTIVE')
            image_ids.append(image_id)
            time.sleep(5)

        # delete images
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images '
                              'WHERE id NOT IN (%s);'
                              'DELETE FROM images WHERE id NOT IN (%s);'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  ','.join(image_ids),
                                  ','.join(image_ids)),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(images))
        for image_id in image_ids:
            self.assertTrue(image_id in [x['id'] for x in images])

        # delete the snapshot
        for image_id in image_ids:
            self.img_client.delete_image(image_id)
            self.img_client.wait_for_image_not_exists(image_id)

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_when_disk_format_is_aki(self):
        """ List of all images should contain the aki image """
        # execute and assert
        aki_image_id = 1
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(aki_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_when_disk_format_is_ari(self):
        """ List of all images should contain the ari image """
        # execute and assert
        ari_image_id = 2
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(ari_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_when_disk_format_is_ami(self):
        """ List of all images should contain the ami image """
        # execute and assert
        ami_image_id = 3
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(ami_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_when_disk_format_is_ovf(self):
        """ List of all images should contain the ovf image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=raw container_format=ovf '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_when_disk_format_is_other(self):
        """ List of all images should contain the other format image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        # update the image
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'UPDATE images SET container_format=\'test\' '
                              'WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_when_architecture_is_x86_64(self):
        """ List of all images should contain the x86-64 image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=x86_64 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_when_architecture_is_i386(self):
        """ List of all images should contain the i386 image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=i386 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_when_architecture_is_other(self):
        """ List of all images should contain the other architecture image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=test < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_when_status_is_active(self):
        """ List of all images should contain the active image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        # Make sure that status of image is active
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_list_images_when_status_is_not_active(self):
        """ List of all images should contain the inactive image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_list_images_when_image_is_in_same_tenant(self):
        """ List of all images should contain images in the same tenant """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user2
        resp, images = self.img_client_for_user2.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # user1
        resp, images = self.img_client_for_user1.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_when_image_unauthenticated_for_user(self):
        """ List of all images should only contain the authenticated image """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user3
        resp, images = self.img_client_for_user3.list_images()
        self.assertEqual('200', resp['status'])
        self.assertFalse(str(image_id) in [x['id'] for x in images])

        # user1
        resp, images = self.img_client_for_user1.list_images()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_with_detail_when_image_amount_is_zero(self):
        """ Detailed list of images should contain the expected image """
        # delete images for test
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images;'
                              'DELETE FROM images;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertEqual(0, len(images))

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_with_detail_when_image_amount_is_one(self):
        """ Detailed list of images should contain the expected image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # delete images for test
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images '
                              'WHERE id != %s;'
                              'DELETE FROM images WHERE id != %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertEqual(1, len(images))
        self.assertEqual(image_id, images[0]['id'])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_with_detail_when_image_amount_is_three(self):
        """ Detailed list of images should contain the expected image """
        # create a server for test
        self.create_server()

        # create an image for test
        image_ids = []
        for i in range(0, 3):
            name = 'server_' + self._testMethodName + '_' + str(i)
            resp, body = self.ss_client.create_image(self.server_id, name)
            alt_img_url = resp['location']
            match = re.search('/images/(?P<image_id>.+)', alt_img_url)
            self.assertIsNotNone(match)
            image_id = match.groupdict()['image_id']
            self.img_client.wait_for_image_status(image_id, 'ACTIVE')
            image_ids.append(image_id)
            time.sleep(5)

        # delete images for test
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'CREATE TABLE IF NOT EXISTS images_wk '
                              'LIKE images;'
                              'DELETE FROM images_wk;'
                              'INSERT INTO images_wk SELECT * from images '
                              'WHERE id NOT IN (%s);'
                              'DELETE FROM images WHERE id NOT IN (%s);'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  ','.join(image_ids),
                                  ','.join(image_ids)),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(images))
        for image_id in image_ids:
            self.assertTrue(image_id in [x['id'] for x in images])

        # delete the snapshot
        for image_id in image_ids:
            self.img_client.delete_image(image_id)
            self.img_client.wait_for_image_not_exists(image_id)

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'INSERT INTO images SELECT * from images_wk;'
                              'DROP TABLE images_wk;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)

    @attr(kind='medium')
    def test_list_images_with_detail_when_disk_format_is_aki(self):
        """ Detailed list of images should contain the aki image """
        # execute and assert
        aki_image_id = 1
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(aki_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_with_detail_when_disk_format_is_ari(self):
        """ Detailed list of images should contain the ari image """
        # execute and assert
        ari_image_id = 2
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(ari_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_with_detail_when_disk_format_is_ami(self):
        """ Detailed list of images should contain the ami image """
        # execute and assert
        ami_image_id = 3
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(ami_image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_with_detail_when_disk_format_is_ovf(self):
        """ Detailed list of images should contain the ovf image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=raw container_format=ovf '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_with_detail_when_disk_format_is_other(self):
        """ Detailed list of images should contain the other format image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        # update the image
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'UPDATE images SET container_format=\'test\' '
                              'WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_with_detail_when_architecture_is_x86_64(self):
        """ Detailed list of images should contain the x86-64 image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=x86_64 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_with_detail_when_architecture_is_i386(self):
        """ Detailed list of images should contain the i386 image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=i386 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_with_detail_when_architecture_is_other(self):
        """ Detailed list of images should contain
            the other architecture image """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=test < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_list_images_with_detail_when_status_is_active(self):
        """ Detailed list of the image should contain the active image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        # Make sure that status of image is active
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_list_images_with_detail_when_status_is_not_active(self):
        """ Detailed list of the image should contain the inactive image """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, images = self.img_client.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_list_images_with_detail_when_image_is_in_same_tenant(self):
        """ Detailed list of the image should contain
            images in the same tenant """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user2
        resp, images = self.img_client_for_user2.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

        # user1
        resp, images = self.img_client_for_user1.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_list_images_with_detail_when_image_unauthenticated_for_user(self):
        """ Detailed list of the image should only contain
            the authenticated image """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user3
        resp, images = self.img_client_for_user3.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertFalse(str(image_id) in [x['id'] for x in images])

        # user1
        resp, images = self.img_client_for_user1.list_images_with_detail()
        self.assertEqual('200', resp['status'])
        self.assertTrue(str(image_id) in [x['id'] for x in images])

    @attr(kind='medium')
    def test_get_image_when_image_exists(self):
        """ Detail of the image should be returned """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])
        self.assertTrue(image['name'])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_get_image_when_image_does_not_exist(self):
        """ Error occurs that the specified image does not exist """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

        # execute and assert
        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Issue #444')
    def test_get_image_when_image_id_is_empty_string(self):
        """ Error occurs that the format of parameter is invalid """
        # execute and assert
        image_id = ''
        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #612')
    def test_get_image_when_image_id_is_string(self):
        """ Returns 400 response """
        # execute and assert
        image_id = 'abc'
        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #612')
    def test_get_image_when_image_id_is_negative_value(self):
        """ Returns 400 response """
        # execute and assert
        image_id = -1
        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #612')
    def test_get_image_when_image_id_is_over_maxint(self):
        """ Error occurs that the format of parameter is invalid """
        # execute and assert
        image_id = sys.maxint + 1
        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_get_image_when_disk_format_is_aki(self):
        """ Detail of the image should be returned """
        # execute and assert
        aki_image_id = 1
        resp, image = self.img_client.get_image(aki_image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(aki_image_id), image['id'])

    @attr(kind='medium')
    def test_get_image_when_disk_format_is_ari(self):
        """ Detail of the image should be returned """
        # execute and assert
        ari_image_id = 2
        resp, image = self.img_client.get_image(ari_image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(ari_image_id), image['id'])

    @attr(kind='medium')
    def test_get_image_when_disk_format_is_ami(self):
        """ Detail of the image should be returned """
        # execute and assert
        ami_image_id = 3
        resp, image = self.img_client.get_image(ami_image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(ami_image_id), image['id'])

    @attr(kind='medium')
    def test_get_image_when_disk_format_is_ovf(self):
        """ Detail of the image should be returned """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=raw container_format=ovf '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(image_id), image['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_get_image_when_disk_format_is_other(self):
        """ Detail of the image should be returned """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      '< %s' % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        # update the image
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'UPDATE images SET container_format=\'test\' '
                              'WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(image_id), image['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_get_image_when_architecture_is_x86_64(self):
        """ Detail of the image should be returned """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=x86_64 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(image_id), image['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_get_image_when_architecture_is_i386(self):
        """ Detail of the image should be returned """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=i386 < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(image_id), image['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_get_image_when_architecture_is_other(self):
        """ Detail of the image should be returned """
        # make an image file
        tmp_file = os.path.abspath(tempfile.mkstemp()[1])

        # create an image for test
        name = 'server_' + self._testMethodName
        out = subprocess.check_output('/opt/openstack/glance/bin/glance add -A tokenAdmin name=%s '
                                      'disk_format=aki container_format=aki '
                                      'architecture=test < %s'
                                      % (name, tmp_file),
                                      cwd=self.config.glance.directory,
                                      shell=True)
        match = re.search('Added new image with ID: (?P<image_id>.+)', out)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(str(image_id), image['id'])

        # reset db
        subprocess.check_call('mysql -u%s -p%s -D glance -e "'
                              'DELETE FROM image_properties '
                              'WHERE image_id = %s;'
                              'DELETE FROM images WHERE id = %s;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password,
                                  image_id,
                                  image_id),
                              shell=True)

        # delete image file
        os.remove(tmp_file)

    @attr(kind='medium')
    def test_get_image_when_status_is_active(self):
        """ Detail of the image should be returned """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])
        self.assertEqual(name, image['name'])
        self.assertEqual('ACTIVE', image['status'])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_get_image_when_status_is_not_active(self):
        """ Detail of the image should be returned """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, image = self.img_client.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])
        self.assertEqual(name, image['name'])
        self.assertNotEqual('ACTIVE', image['status'])

        # delete the snapshot
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

    @attr(kind='medium')
    def test_get_image_when_image_is_in_same_tenant(self):
        """ Detail of the image should be returned """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user2
        resp, image = self.img_client_for_user2.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])

        # user1
        resp, image = self.img_client_for_user1.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])

    @attr(kind='medium')
    def test_get_image_when_unauthenticated_for_user(self):
        """ Detail of the image should only contain the authenticated image """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user3
        resp, image = self.img_client_for_user3.get_image(image_id)
        self.assertEqual('404', resp['status'])

        # user1
        resp, image = self.img_client_for_user1.get_image(image_id)
        self.assertEqual('200', resp['status'])
        self.assertTrue(image)
        self.assertEqual(image_id, image['id'])

    @attr(kind='medium')
    def test_delete_image_when_image_exists(self):
        """ The specified image should be deleted """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('204', resp['status'])

        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #455')
    def test_delete_image_when_image_does_not_exist(self):
        """ Returns 404 response """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # delete a image for test
        self.img_client.delete_image(image_id)
        self.img_client.wait_for_image_not_exists(image_id)

        # execute and assert
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #610')
    def test_delete_image_when_image_id_is_empty_string(self):
        """ Returns 400 response """
        # execute and assert
        image_id = ''
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_image_id_is_string(self):
        """ Returns 400 response """
        # execute and assert
        image_id = 'abc'
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_image_id_is_negative_value(self):
        """ Returns 400 response """
        # execute and assert
        image_id = -1
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_image_id_is_over_maxint(self):
        """ Returns 400 response """
        # execute and assert
        image_id = sys.maxint + 1
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('400', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_status_is_active(self):
        """ The specified image should be deleted """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('204', resp['status'])

        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_status_is_not_active(self):
        """ The specified image should be deleted """
        # create a server for test
        self.create_server()

        # create an image for test
        name = 'server_' + self._testMethodName
        resp, body = self.ss_client.create_image(self.server_id, name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']

        # execute and assert
        resp, body = self.img_client.delete_image(image_id)
        self.assertEqual('204', resp['status'])

        resp, body = self.img_client.get_image(image_id)
        self.assertEqual('404', resp['status'])

    @attr(kind='medium')
    def test_delete_image_when_image_is_in_same_tenant(self):
        """ The specified image should be deleted """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user2
        resp, body = self.img_client_for_user2.delete_image(image_id)
        self.assertEqual('204', resp['status'])

    @attr(kind='medium')
    @tests.skip_test('Ignore this testcase for Bug #607')
    def test_delete_image_when_unauthenticated_for_user(self):
        """ Only the authenticated image should be deleted """
        # create a server for test
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = 'server_' + self._testMethodName
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.ss_client_for_user1.create_server(name,
                                                    self.image_ref,
                                                    self.flavor_ref,
                                                    accessIPv4=accessIPv4,
                                                    accessIPv6=accessIPv6,
                                                    personality=personality)
        self.ss_client_for_user1.wait_for_server_status(server['id'], 'ACTIVE')

        # create an image for test
        resp, body = self.ss_client_for_user1.create_image(server['id'], name)
        alt_img_url = resp['location']
        match = re.search('/images/(?P<image_id>.+)', alt_img_url)
        self.assertIsNotNone(match)
        image_id = match.groupdict()['image_id']
        self.img_client_for_user1.wait_for_image_status(image_id, 'ACTIVE')

        # execute and assert
        # user3
        resp, body = self.img_client_for_user3.delete_image(image_id)
        self.assertEqual('401', resp['status'])

        # user1
        resp, body = self.img_client_for_user1.delete_image(image_id)
        self.assertEqual('204', resp['status'])
