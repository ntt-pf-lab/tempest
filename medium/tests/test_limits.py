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


class TestBase(unittest.TestCase):

    config = config

    def setUp(self):
        self.testing_processes = []
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

    def tearDown(self):
        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]

    def get_quota_data_from_mysql(self, resource=None):
        if resource is not None:
            if not isinstance(resource, list):
                resource = [resource]
            resource_sql = 'AND (%s)' % ' OR '.join("resource='%s'" % name
                                                    for name in resource)
        else:
            resource_sql = ''
        s = subprocess.check_output("""mysql -u %s -p%s nova -Ns -e "
                                       SELECT * FROM quotas
                                       WHERE project_id='%s'
                                             %s;" """\
                                         % (self.config.mysql.user,
                                            self.config.mysql.password,
                                            self.config.nova.username,
                                            resource_sql),
                                         shell=True)
        return s

    def request_for_limit(self, url, method='GET', body=None):
        http_obj = self.rest_client.http_obj
        token = self.rest_client.token

        headers = {'X-Auth-Token': token}
        if body is not None:
            headers['content-type'] = 'application/json'
            body = json.dumps(body)
        resp, body = http_obj.request(url,
                method=method, body=body, headers=headers)
        if resp['content-type'] == 'application/json':
            body = json.loads(body)
        return resp, body

    def _tenant_url(self, tenant_id=None):
        if tenant_id is None:
            return self.rest_client.base_url
        else:
            return self.rest_client.base_url.rsplit('/', 1)[0]\
                   + '/' + tenant_id

    def _quota_sets_url(self, tenant_id=None, defaults=False):
        tenant_url = self._tenant_url(tenant_id=tenant_id)
        if defaults:
            return tenant_url + '/os-quota-sets/defaults'
        else:
            return tenant_url + '/os-quota-sets'
            # XXX treat this strange url as valid until the bug #427 is fixed.
            # if tenant_id is None:
            #     tenant_id = tenant_url.rsplit('/', 1)[1]
            # return tenant_url + '/os-quota-sets/%s' % tenant_id

    def get_absolute_limits(self, tenant_id=None):
        return self.request_for_limit(
                self._tenant_url(tenant_id=tenant_id) + '/limits')

    def get_limits(self, tenant_id=None, defaults=False):
        return self.request_for_limit(self._quota_sets_url(tenant_id=tenant_id,
                                                           defaults=defaults))

    def put_limits(self, tenant_id=None, **kwargs):
        url = self._quota_sets_url(tenant_id=tenant_id)
        return self.request_for_limit(url, method='PUT',
                                      body={'quota_set': kwargs})


class LimitsTest(TestBase):

    # magic number of default quota of cores.
    cores = 20

    def setUp(self):
        super(LimitsTest, self).setUp()

        # nova.
        nova_api = NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port)
        self.testing_processes.append(nova_api)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

    @attr(kind='medium')
    def test_A00_04_absolute_limits(self):
        resp, body = self.get_absolute_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['limits']['absolute']['maxTotalCores'],
                         self.cores)

    @attr(kind='medium')
    def test_A00_145_get_stored_limit(self):
        cores = 5

        # update
        resp, body = self.put_limits(cores=cores)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

        # verify
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

    @attr(kind='medium')
    def test_A00_146_get_limit_from_unknown_tenant(self):
        resp, _body = self.get_limits(tenant_id='unknown')
        self.assertEqual(resp.status, 404)

    @attr(kind='medium')
    def test_A00_147_get_limit(self):
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], self.cores)

    @attr(kind='medium')
    def test_A00_148_update_limits(self):
        cores = 5

        # update
        resp, body = self.put_limits(cores=cores)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

        # verify
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

    @attr(kind='medium')
    def test_A00_149_update_limits_with_unknown_tenant(self):
        cores = 5

        # update
        resp, body = self.put_limits(tenant_id='unknown', cores=cores)
        self.assertEqual(resp.status, 404)

    @attr(kind='medium')
    def test_A00_151_update_limits(self):
        cores = 5

        # update
        resp, body = self.put_limits(cores=cores)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

        # verify
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

    @attr(kind='medium')
    def test_A00_152_update_some_limits(self):
        cores = 5
        volumes = 1

        # update
        resp, body = self.put_limits(cores=cores, volumes=volumes)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)
        self.assertEqual(body['quota_set']['volumes'], volumes)

        # verify
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)
        self.assertEqual(body['quota_set']['volumes'], volumes)

    @attr(kind='medium')
    def test_A00_153_create_limits(self):
        cores = 5

        # prepare
        s = self.get_quota_data_from_mysql('cores')
        self.assertEqual(len(s.split()), 0, "Must be no quota")

        # update
        resp, body = self.put_limits(cores=cores)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

        # verify
        resp, body = self.get_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

    @attr(kind='medium')
    def test_A00_154_update_unknown_limits(self):
        # prepare
        s = self.get_quota_data_from_mysql()
        self.assertEqual(len(s.split()), 0, "Must be no quota")

        # update
        resp, body = self.put_limits(unknown=1)
        self.assertEqual(resp.status, 404)

        # verify
        s = self.get_quota_data_from_mysql()
        self.assertEqual(len(s.split()), 0, "Must be no quota")

    @attr(kind='medium')
    def test_A00_155_default_limits(self):
        resp, body = self.get_limits(defaults=True)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], self.cores)

    @attr(kind='medium')
    def test_A00_156_default_limits_from_unknown_tenant(self):
        # update
        resp, body = self.get_limits(tenant_id='unknown', defaults=True)
        self.assertEqual(resp.status, 404)


class AppliedFlagValueTest(TestBase):

    cores = 33

    def setUp(self):
        super(AppliedFlagValueTest, self).setUp()
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

    @attr(kind='medium')
    def test_A00_02_absolute_limits(self):
        resp, body = self.get_absolute_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['limits']['absolute']['maxTotalCores'],
                         self.cores)

    @attr(kind='medium')
    def test_A00_03_use_stored_value_instead_of_flags(self):
        cores = 5

        # update
        resp, body = self.put_limits(cores=cores)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['quota_set']['cores'], cores)

        resp, body = self.get_absolute_limits()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body['limits']['absolute']['maxTotalCores'], cores)
