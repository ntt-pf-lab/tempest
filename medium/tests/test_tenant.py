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
import json
import subprocess
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
from medium.tests.processes import (
        KeystoneProcess,
        NovaApiProcess)
from medium.tests.test_through import config, tearDownModule

config = config
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # keystone.
    environ_processes.append(KeystoneProcess(
            config.keystone.directory,
            config.keystone.config,
            config.keystone.host,
            config.keystone.port))

    for process in environ_processes:
        process.start()
    time.sleep(10)

tearDownModule = tearDownModule


class TenantTest(unittest.TestCase):

    config = config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        # take a rest client from storm internal.
        self.rest_client = self.os.servers_client.client

        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))

        # reset db.
        subprocess.check_call('mysql -u%s -p%s -e "'
                              'DROP DATABASE IF EXISTS nova;'
                              'CREATE DATABASE nova;'
                              '"' % (
                                  self.config.mysql.user,
                                  self.config.mysql.password),
                              shell=True)
        subprocess.call('bin/nova-manage db sync',
                        cwd=self.config.nova.directory, shell=True)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

        # create users.
        subprocess.check_call('bin/nova-manage user create '
                              '--name=%s --access=secrete --secret=secrete'\
                                      % self.config.nova.username,
                              cwd=self.config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('bin/nova-manage project create '
                              '--project=1 --user=%s'\
                                      % self.config.nova.username,
                              cwd=self.config.nova.directory, shell=True)

    def tearDown(self):
        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            (id, name, state) = line.split()
            if state == 'running':
                subprocess.check_call('virsh destroy %s' % id, shell=True)
            subprocess.check_call('virsh undefine %s' % name, shell=True)

        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]

    @attr(kind='medium')
    def test_A00_01_version(self):
        http_obj = self.rest_client.http_obj
        version_top_url = self.rest_client.base_url.rsplit('/', 1)[0] + '/'
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        resp, body = http_obj.request(version_top_url, headers=headers)

        self.assertEqual(resp.status, 200)
        body = json.loads(body)
        self.assertEqual(body['version']['id'], 'v1.1')

    @attr(kind='medium')
    def test_A00_01_tenant_not_existing(self):
        http_obj = self.rest_client.http_obj
        version_top_url, tenant_name = self.rest_client.base_url.rsplit('/', 1)
        tenant_not_existing_url = version_top_url + '/' + tenant_name + '1'
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        resp, body = http_obj.request(tenant_not_existing_url, headers=headers)

        self.assertEqual(resp.status, 404)
