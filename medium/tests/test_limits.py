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

tearDownModule = tearDownModule


class TestBase(unittest.TestCase):

    config = config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        # take a rest client from storm internal.
        self.rest_client = self.os.servers_client.client

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

        # create users.
        subprocess.check_call('bin/nova-manage user create '
                              '--name=admin --access=secrete --secret=secrete',
                              cwd=self.config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('bin/nova-manage project create '
                              '--project=1 --user=admin',
                              cwd=self.config.nova.directory, shell=True)


class LimitsTest(TestBase):

    def setUp(self):
        super(LimitsTest, self).setUp()
        self.testing_processes = []

        # nova.
        nova_api = NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port)
        self.testing_processes.append(nova_api)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

    def tearDown(self):
        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]

    @attr(kind='medium')
    def test_limits_by_default(self):
        http_obj = self.rest_client.http_obj
        limits_url = self.rest_client.base_url + '/limits'
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        resp, body = http_obj.request(limits_url,
                                      headers=headers)

        self.assertEqual(resp.status, 200)
        body = json.loads(body)
        self.assertEqual(body['limits']['absolute']['maxTotalCores'],
                         20)  # magic number of default quota of cores.


class ApplyingFlagValueTest(TestBase):

    cores = 33

    def setUp(self):
        super(ApplyingFlagValueTest, self).setUp()
        self.testing_processes = []

        # nova.
        nova_api = NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port)
        nova_api.command += ' --quota_cores=%d' % self.cores
        self.testing_processes.append(nova_api)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

    def tearDown(self):
        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]

    @attr(kind='medium')
    def test_limits_with_flags(self):
        http_obj = self.rest_client.http_obj
        limits_url = self.rest_client.base_url + '/limits'
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        resp, body = http_obj.request(limits_url,
                                      headers=headers)

        self.assertEqual(resp.status, 200)
        body = json.loads(body)
        self.assertEqual(body['limits']['absolute']['maxTotalCores'],
                         self.cores)
