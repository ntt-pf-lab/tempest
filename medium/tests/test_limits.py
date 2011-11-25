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
                              '--name=%s --access=secrete --secret=secrete'\
                                      % self.config.nova.username,
                              cwd=self.config.nova.directory, shell=True)

        # create projects.
        subprocess.check_call('bin/nova-manage project create '
                              '--project=1 --user=%s'\
                                      % self.config.nova.username,
                              cwd=self.config.nova.directory, shell=True)

    def request_for_limit(self, url, method='GET', body=None):
        http_obj = self.rest_client.http_obj
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        if body is not None:
            headers['content-type'] = 'application/json'
            body = json.dumps(body)
        resp, body = http_obj.request(url,
                method=method, body=body, headers=headers)
        self.assertEqual(resp.status, 200)
        if resp['content-type'] == 'application/json':
            body = json.loads(body)
        return resp, body


class LimitsTest(TestBase):

    # magic number of default quota of cores.
    cores = 20

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
    def test_absolute_limits_by_default(self):
        resp, body = self.request_for_limit(self.rest_client.base_url\
                                            + '/limits')
        self.assertEqual(body['limits']['absolute']['maxTotalCores'],
                         self.cores)

    @attr(kind='medium')
    def test_default_limits_by_default(self):
        resp, body = self.request_for_limit(self.rest_client.base_url\
                                            + '/os-quota-sets/admin')
        self.assertEqual(body['quota_set']['cores'], self.cores)

    @attr(kind='medium')
    def test_update_limit_on_demand(self):
        cores = 5

        # update
        resp, body = self.request_for_limit(self.rest_client.base_url\
                                            + '/os-quota-sets/admin',
                                            method='PUT',
                                            body={'quota_set':
                                                    {'cores': cores}})
        self.assertEqual(body['quota_set']['cores'], cores)

        resp, body = self.request_for_limit(self.rest_client.base_url\
                                            + '/os-quota-sets/admin')
        self.assertEqual(body['quota_set']['cores'], cores)


class AppliedFlagValueTest(LimitsTest):

    cores = 33

    def setUp(self):
        super(LimitsTest, self).setUp()
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
