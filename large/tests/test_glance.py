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
import os
import subprocess
import tempfile
import time
import logging

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
import utils
from kong import tests
from storm.common.rest_client import LoggingFeature
from storm.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

#from medium.tests.processes import (
#        GlanceRegistryProcess, GlanceApiProcess,
#        KeystoneProcess,
#        QuantumProcess, QuantumPluginOvsAgentProcess,
#        NovaApiProcess, NovaComputeProcess,
#        NovaNetworkProcess, NovaSchedulerProcess)

LOG = logging.getLogger("large.tests.test_glance")
messages = []


def setUpModule(module):
    pass


def tearDownModule(module):
    print "\nAll glance tests done."


class FunctionalTest(unittest.TestCase):

    def setUp(self):
        default_config = storm.config.StormConfig('etc/large.conf')
        self.db = DBController(default_config)
        self.config = default_config

    def tearDown(self):
        pass


class DBController(object):
    def __init__(self, config):
        self.config = config

    def exec_mysql(self, sql, database='nova'):
        LOG.debug("Execute sql %s" % sql)
        exec_sql = 'mysql -h %s -u %s -p%s %s -Ns -e "' + sql + '"'
        results = subprocess.check_output(exec_sql % (
                                          self.config.mysql.host,
                                          self.config.mysql.user,
                                          self.config.mysql.password,
                                          database),
                                          shell=True)
        LOG.debug("SQL Execution Result %s" % results)

        return [tuple(result.split('\t'))
                    for result in results.split('\n') if result]


class GlanceWrapper(object):
    def __init__(self, token, config):
        self.path = config.glance.directory
        self.conf = config.glance.api_config
        self.host = config.glance.host
        self.port = config.glance.port
        self.token = token

    def _glance(self, action, params, yes=None):
        cmd = "glance -A %s -H %s -p %s %s %s" %\
             (self.token, self.host, self.port, action, params)
        if yes:
            cmd = ("yes %s|" % yes) + cmd
        LOG.debug('cmd=' + str(cmd))
        #raise Exception('cmd=' + str(cmd))
        result = subprocess.check_output(cmd, cwd=self.path, shell=True)
        return result

    def index(self):
        result = self._glance('index', '')
        return result

    def add(self, name=None, is_public=None, disk_format=None,
            container_format=None, location=None):
        params = ''
        if name is not None:
            params += 'name=%s ' % name
        if is_public is not None:
            params += 'is_public=%s ' % is_public
        if disk_format is not None:
            params += 'disk_format=%s ' % disk_format
        if container_format is not None:
            params += 'container_format=%s ' % container_format
        if location is not None:
            params += '< %s' % location
        result = self._glance('add', params)
        # parse add new image ID: <image_id>
        if result:
            splited = str(result).split()
            return splited[splited.count(splited)-1]

    def delete(self, image_id=None):
        result = self._glance('delete', image_id, yes="y")
        if result:
            return image_id

    def detail(self, image_name=None):
        if image_name:
            params = "name=%s" % image_name
        else:
            params = ""
        result = self._glance('details', params)
        return result

#    def update(self, image_id, image_name):
#        params = "%s name=%s" % (image_id, image_name)
#        result = self._glance('update', params)
#        return result
    def update(self, image_id='', name=None, is_public=None, disk_format=None,
               container_format=None, location=None):
        params = '%s ' % image_id
        if name is not None:
            params += 'name=%s ' % name
        if is_public is not None:
            params += 'is_public=%s ' % is_public
        if disk_format is not None:
            params += 'disk_format=%s ' % disk_format
        if container_format is not None:
            params += 'container_format=%s ' % container_format
        if location is not None:
            params += 'location=%s' % location
        result = self._glance('update', params)
        return result


class GlanceTest(FunctionalTest):

    def setUp(self):
        super(GlanceTest, self).setUp()
        self.token_client = TokenClient(self.config)
        token = self.token_client.get_token(self.config.keystone.user,
                                            self.config.keystone.password,
                                            self.config.keystone.tenant_name)
        self.glance = GlanceWrapper(token, self.config)
#        self._load_client(self.config)

#    def _load_client(self, config):
#        self.token_client = TokenClient(config)
#        token = self.token_client.get_token(config.keystone.user,
#                                            config.keystone.password,
#                                            config.keystone.tenant_name)
#        self.glance = GlanceWrapper(token, config)

    def test_glance_index(self):
        # execute
        result = self.glance.index()

        # assert
        images = result.split('\n')[2:-1]
        self.assertTrue(images)

    def test_glance_index_not_authorized(self):
        # execute and assert
        glance_not_authorized = GlanceWrapper('xxx', self.config)
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            glance_not_authorized.index()
        exception = cm.exception
        # "Not authorized to make this request..."
        self.assertIn('Not authorized', exception.output)

#    def test_glance_index_when_db_stopped(self):
#        # stop db
#        utils.stopDBService()
#        # add cleanup
#        self.addCleanup(utils.startDBService)
#
#        # execute and assert
#        with self.assertRaises(subprocess.CalledProcessError) as cm:
#            self.glance.index()
#        exception = cm.exception
#        #TODO
#        # "Not authorized to make this request.
#        # Check your credentials (OS_AUTH_USER, OS_AUTH_KEY, ...)..."
#        self.assertIn('Not authorized', exception.output)

    def test_glance_details(self):
        # execute
        result = self.glance.detail()
        self.assertTrue(result)

    def test_glance_details_with_name(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute
        result = self.glance.detail(name)
        LOG.debug('result=' + str(result))
        self.assertTrue(result)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_details_with_non_existent_name(self):
        # execute
        result = self.glance.detail('not_exist')
        self.assertEqual('', result)

    def test_glance_details_not_authorized(self):
        # execute and assert
        glance_not_authorized = GlanceWrapper('xxx', self.config)
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            glance_not_authorized.detail()
        exception = cm.exception
        # "Not authorized to make this request..."
        self.assertIn('Not authorized', exception.output)

#    def test_glance_details_when_db_stopped(self):
#        # stop db
#        utils.stopDBService()
#        # add cleanup
#        self.addCleanup(utils.startDBService)
#
#        # execute and assert
#        with self.assertRaises(subprocess.CalledProcessError) as cm:
#            self.glance.detail()
#        exception = cm.exception
#        #TODO
#        # "Not authorized to make this request.
#        # Check your credentials (OS_AUTH_USER, OS_AUTH_KEY, ...)..."
#        self.assertIn('Not authorized', exception.output)

    def test_glance_add(self):
        # execute
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertTrue(os.path.exists(abs_path))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_with_no_is_public(self):
        # execute
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = None
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertTrue(os.path.exists(abs_path))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_when_is_public_unexpected_value(self):
        # execute
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'xxx'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        self.assertEqual('0', utils.get_image_is_public_in_db(self.config,
                                                              image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertTrue(os.path.exists(abs_path))

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_with_no_disk_format(self):
        # execute
        name = self._testMethodName
        disk_format = None
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertTrue(os.path.exists(abs_path))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_with_no_container_format(self):
        # execute
        name = self._testMethodName
        disk_format = 'ami'
        container_format = None
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertTrue(os.path.exists(abs_path))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_not_authorized(self):
        # execute and assert
        glance_not_authorized = GlanceWrapper('xxx', self.config)
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            glance_not_authorized.add(name, is_public, disk_format,
                                      container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error: 401 Unauthorized..."
        self.assertIn('401 Unauthorized', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

#    def test_glance_add_when_db_stopped(self):
#        # stop db
#        utils.stopDBService()
#        # add cleanup
#        self.addCleanup(utils.startDBService)
#
#        # execute and assert
#        name = self._testMethodName
#        disk_format = 'ami'
#        container_format = 'ami'
#        is_public = 'True'
#        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
#        with self.assertRaises(subprocess.CalledProcessError) as cm:
#            self.glance.add(name, is_public, disk_format,
#                            container_format, path_to_image)
#        exception = cm.exception
#        #TODO
#        # "Failed to add image. Got error:\n401 Unauthorized..."
#        self.assertIn('401 Unauthorized', exception.output)
#
#        # add cleanup
#        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_with_no_name(self):
        # execute and assert
        name = None
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Please specify a name for the image using name=VALUE"
        self.assertIn('Please specify a name', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_when_name_length_is_over_255(self):
        # execute and assert
        name = 'a' * 256
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error:\n400 Bad Request\n\nThe server..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_when_disk_format_unexpected_value(self):
        # execute and assert
        name = self._testMethodName
        disk_format = 'xxx'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error:\n400 Bad Request\n\nThe server..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_when_container_format_unexpected_value(self):
        # execute and assert
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'xxx'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error:\n400 Bad Request\n\nThe server..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    def test_glance_add_when_disk_format_and_container_format_mismatch(self):
        # execute and assert
        name = self._testMethodName
        disk_format = 'vhd'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error:\n400 Bad Request\n\nThe server..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(os.remove, path_to_image)

    @tests.skip_test('No command response returned')
    def test_glance_add_with_no_path_to_image(self):
        # execute and assert
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = None
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.add(name, is_public, disk_format,
                            container_format, path_to_image)
        exception = cm.exception
        # "Failed to add image. Got error:\n400 Bad Request\n\nThe server..."
        self.assertIn('400 Bad Request', exception.output)

    def test_glance_add_when_path_to_image_not_exist(self):
        # execute and assert
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = '/not/exist'
        self.assertRaises(subprocess.CalledProcessError,
                          self.glance.add,
                          name, is_public, disk_format, container_format,
                          path_to_image)

    def test_glance_update(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute
        alt_name = self._testMethodName + '_2'
        alt_disk_format = 'raw'
        alt_container_format = 'ovf'
        alt_is_public = 'False'
        alt_path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        self.glance.update(image_id, alt_name, alt_is_public, alt_disk_format,
                           alt_container_format,
                           'file://' + alt_path_to_image)

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        self.assertEqual(alt_name, utils.get_image_name_in_db(self.config,
                                                              image_id))
        self.assertEqual('0', utils.get_image_is_public_in_db(self.config,
                                                              image_id))
        self.assertEqual(alt_disk_format,
                         utils.get_image_disk_format_in_db(self.config,
                                                           image_id))
        self.assertEqual(alt_container_format,
                         utils.get_image_container_format_in_db(self.config,
                                                                image_id))
        self.assertEqual('file://' + alt_path_to_image,
                         utils.get_image_location_in_db(self.config, image_id))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)
        self.addCleanup(os.remove, alt_path_to_image)

    def test_glance_update_with_is_public_unexpected_value(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute
        alt_is_public = 'xxx'
        self.glance.update(image_id, is_public=alt_is_public)

        # assert db
        self.assertEqual('0', utils.get_image_is_public_in_db(self.config,
                                                              image_id))

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_not_authorized(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_name = self._testMethodName + '_2'
        glance_not_authorized = GlanceWrapper('xxx', self.config)
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            glance_not_authorized.update(image_id, name=alt_name)
        exception = cm.exception
        # "Failed to update image. Got error:\n401 Unauthorized..."
        self.assertIn('401 Unauthorized', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

#    def test_glance_update_when_db_stopped(self):
#        # create a image for test
#        name = self._testMethodName
#        disk_format = 'ami'
#        container_format = 'ami'
#        is_public = 'True'
#        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
#        image_id = self.glance.add(name, is_public, disk_format,
#                                   container_format, path_to_image)
#        LOG.debug('image_id=' + str(image_id))
#
#        # stop db
#        utils.stopDBService()
#        # add cleanup
#        self.addCleanup(utils.startDBService)
#
#        # execute and assert
#        alt_name = self._testMethodName + '_2'
#        with self.assertRaises(subprocess.CalledProcessError) as cm:
#            self.glance.update(image_id, name=alt_name)
#        exception = cm.exception
#        #TODO
#        # "Failed to update image. Got error:\n401 Unauthorized..."
#        self.assertIn('401 Unauthorized', exception.output)
#
#        # add cleanup
#        #self.addCleanup(self.glance.delete, image_id)
#        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_when_name_length_is_over_255(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_name = 'a' * 256
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.update(image_id, name=alt_name)
        exception = cm.exception
        # "No image with ID None was found..."
        self.assertEqual('No image with ID', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_with_disk_format_unexpected_value(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_disk_format = 'xxx'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.update(image_id, disk_format=alt_disk_format)
        exception = cm.exception
        # "Failed to update image. Got error:\n400 Bad Request..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_with_container_format_unexpected_value(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_container_format = 'xxx'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.update(image_id, container_format=alt_container_format)
        exception = cm.exception
        # "Failed to update image. Got error:\n400 Bad Request..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_when_disk_format_and_container_format_mismatch(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_disk_format = 'vhd'
        alt_container_format = 'ami'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.update(image_id,
                               disk_format=alt_disk_format,
                               container_format=alt_container_format)
        exception = cm.exception
        # "Failed to update image. Got error:\n400 Bad Request..."
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_update_when_path_to_image_not_exist(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        alt_path_to_image = '/not/exist'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.update(image_id, location=alt_path_to_image)
        exception = cm.exception
        # "Failed to update image. Got error:\n400 Bad Request..."
        #TODO
        self.assertIn('400 Bad Request', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_delete(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute
        result = self.glance.delete(image_id)
        self.assertEqual(image_id, result)

        # assert db
        self.assertTrue(utils.exist_image_in_db(self.config, image_id))
        self.assertEqual('1', utils.get_image_deleted_in_db(self.config,
                                                            image_id))
        # assert image file
        abs_path = os.path.join(self.config.glance.directory,
                                'images', image_id)
        self.assertFalse(os.path.exists(abs_path))

    def test_glance_delete_not_authorized(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        glance_not_authorized = GlanceWrapper('xxx', self.config)
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            glance_not_authorized.delete(image_id)
        exception = cm.exception
        # "...glance.common.exception.NotAuthorized: 401 Unauthorized"
        #self.assertIn('401 Unauthorized', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

#    def test_glance_delete_when_db_stopped(self):
#        # create a image for test
#        name = self._testMethodName
#        disk_format = 'ami'
#        container_format = 'ami'
#        is_public = 'True'
#        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
#        image_id = self.glance.add(name, is_public, disk_format,
#                                   container_format, path_to_image)
#        LOG.debug('image_id=' + str(image_id))
#
#        # stop db
#        utils.stopDBService()
#        # add cleanup
#        self.addCleanup(utils.startDBService)
#
#        # execute and assert
#        with self.assertRaises(subprocess.CalledProcessError) as cm:
#            self.glance.delete(image_id)
#        exception = cm.exception
#        #self.assertEqual('401 Unauthorized', exception.output)
#
#        # add cleanup
#        #self.addCleanup(self.glance.delete, image_id)
#        self.addCleanup(os.remove, path_to_image)

    def test_glance_delete_with_no_image_id(self):
        # create a image for test
        name = self._testMethodName
        disk_format = 'ami'
        container_format = 'ami'
        is_public = 'True'
        path_to_image = os.path.abspath(tempfile.mkstemp()[1])
        image_id = self.glance.add(name, is_public, disk_format,
                                   container_format, path_to_image)
        LOG.debug('image_id=' + str(image_id))

        # execute and assert
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.delete()
        exception = cm.exception
        # "No image with ID None was found..."
        self.assertIn('No image with ID', exception.output)

        # cleanup
        self.addCleanup(self.glance.delete, image_id)
        self.addCleanup(os.remove, path_to_image)

    def test_glance_delete_with_non_existent_image_id(self):
        # execute and assert
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.glance.delete('999999')  # not exist
        exception = cm.exception
        # "No image with ID 999999 was found..."
        self.assertIn('No image with ID', exception.output)
