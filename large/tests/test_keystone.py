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
import subprocess
import logging

import unittest2 as unittest
from nose.plugins.attrib import attr

import tempest.config
from kong import tests
from tempest import openstack
from tempest.common import rest_client
from tempest.common.rest_client import RestClientLogging
from tempest.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

LOG = logging.getLogger("large.tests.test_keystone")
messages = []

def setUpModule(module):
    rest_client.rest_logging = KeystoneLogging()

def tearDownModule(module):
    print "\nAll keystone tests done. Dump message infos."
    for m in messages:
        print "Test: %s\nMessages %s" % m

class KeystoneLogging(RestClientLogging):

    def do_auth(self, creds):
        LOG.info("Authenticate %s" % creds)

    def do_request(self, req_url, method, headers, body):
        LOG.info(">>> Send Request %s %s" % (method, req_url))
        LOG.debug(">>> Headers %s" % headers)
        LOG.debug(">>> Request Body %s" % body)

    def do_response(self, resp, body):
        LOG.info("<<< Receive Response %s" % resp)
        LOG.debug("<<< Response Body %s" % body)

class FunctionalTest(unittest.TestCase):

    def setUp(self):
        default_config = tempest.config.TempestConfig('etc/large.conf')
        self.os = openstack.Manager(default_config)
        self.client = self.os.keystone_client
        self.token_client = TokenClient(default_config)
        self.data = DataGenerator(self.client)
        self.db = DBController(default_config)

    def tearDown(self):
        self.data.teardown_all()

    @attr(kind='large')
    def swap_user(self, user, password, tenant_name):
        config = tempest.config.TempestConfig('etc/large.conf')
        config.identity.conf.set('identity', 'username', user)
        config.identity.conf.set('identity', 'password', password)
        config.identity.conf.set('identity', 'tenant_name', tenant_name)
        self.os = openstack.Manager(config)
        self.client = self.os.keystone_client

    @attr(kind='large')
    def diable_user(self, user_name):
        user = self.get_user_by_name(user_name)
        self.client.enable_disable_user(user['id'], False)

    @attr(kind='large')
    def diable_tenant(self, tenant_name):
        tenant = self.get_tenant_by_name(tenant_name)
        self.client.update_tenant(tenant['id'], tenant['description'], False)

    @attr(kind='large')
    def get_user_by_name(self, name):
        _, body = self.client.get_users()
        users = body['users']['values']
        user = [u for u in users if u['name'] == name]
        if len(user) > 0:
            return user[0]

    @attr(kind='large')
    def get_tenant_by_name(self, name):
        _, body = self.client.get_tenants()
        tenants = body['tenants']['values']
        tenant = [t for t in tenants if t['name'] == name]
        if len(tenant) > 0:
            return tenant[0]

    @attr(kind='large')
    def get_role_by_name(self, name):
        _, body = self.client.get_roles()
        roles = body['roles']['values']
        role = [r for r in roles if r['name'] == name]
        if len(role) > 0:
            return role[0]

    @attr(kind='large')
    def expire_token(self, user_id, tenant_id):
        sql = "update token set expires = '2000-01-01' where user_id=%s and \
                tenant_id=%s" % (user_id, tenant_id)
        self.db.exec_mysql(sql)

    @attr(kind='large')
    def remove_token(self, user_id, tenant_id):
        sql = "delete from token where user_id=%s and tenant_id=%s" % \
                (user_id, tenant_id)
        self.db.exec_mysql(sql)


class DBController(object):
    def __init__(self, config):
        self.config = config

    def exec_mysql(self, sql):
        LOG.debug("Execute sql %s" % sql)
        exec_sql = 'mysql -h %s -u %s -p%s keystone -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.host,
                                         self.config.mysql.user,
                                         self.config.mysql.password),
                                         shell=True)
        LOG.debug("SQL Execution Result %s" % result)


class DataGenerator(object):
    def __init__(self, client):
        self.client = client
        self.users = []
        self.tenants = []
        self.roles = []
        self.role_name = None

    def setup_one_user(self):
        _, tenant = self.client.create_tenant("test_tenant1",
                                            "tenant_for_test")
        _, user = self.client.create_user("test_user1", "password",
                                    tenant['tenant']['id'], "user1@mail.com")
        self.tenants.append(tenant['tenant'])
        self.users.append(user['user'])

    def setup_role(self):
        _, services = self.client.get_services()
        services = services['OS-KSADM:services']
        service_name = services[0]['name']
        service_id = services[0]['id']
        _, roles = self.client.create_role(service_name + ':test1' ,
                                        'Test role', service_id)
        self.role_name = service_name + ':test1'
        self.roles.append(roles['role'])

    def teardown_all(self):
        for u in self.users:
            self.client.delete_user(u['id'])
        for t in self.tenants:
            self.client.delete_tenant(t['id'])
        for r in self.roles:
            self.client.delete_role(r['id'])

class KeystoneTest(FunctionalTest):

    @attr(kind='large')
    def test_get_tenants(self):
        self.data.setup_one_user()
        _, body = self.client.get_tenants()
        tenants = body['tenants']['values']
        self.assertIn('test_tenant1', [t['name'] for t in tenants],
                        "test_tenant1 should be include.")

    @attr(kind='large')
    def test_get_tenants_with_no_grant(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.get_tenants()
        self.assertEqual('401', resp['status'])
        messages.append(('test_get_tenants_with_no_grant',body))

    @attr(kind='large')
    def test_get_tenants_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.get_tenants()
        self.assertEqual('403', resp['status'])
        messages.append(('test_get_tenants_with_expired_user', body))

    @attr(kind='large')
    def test_get_tenants_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.get_tenants()
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_tenants_with_no_token', body))

    @attr(kind='large')
    def test_create_tenants(self):
        _, body = self.client.create_tenant("test_tenant1", "tenant_for_test")
        self.data.tenants.append(body['tenant'])
        self.assertEquals('test_tenant1', body['tenant']['name'])
        self.assertEquals('tenant_for_test', body['tenant']['description'])
        messages.append(('test_create_tenants', body))

    @attr(kind='large')
    def test_create_tenants_with_no_grant(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.create_tenant("test_no_grant", "not created")
        self.assertEqual('401', resp['status'])
        messages.append(('test_create_tenants_with_no_grant',body))

    @attr(kind='large')
    def test_create_tenants_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.create_tenant('test_expired', 'not created')
        self.assertEqual('403', resp['status'])
        messages.append(('test_create_tenants_with_expired_user', body))

    @attr(kind='large')
    def test_create_tenants_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.create_tenant('test_no_token', 'not_created')
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_tenants_with_no_token', body))

    @attr(kind='large')
    def test_create_tenants_conflict(self):
        self.data.setup_one_user()
        resp, body = self.client.create_tenant("test_tenant1",
                                            "tenant_for_test")
        self.assertEqual('409', resp['status'])
        messages.append(('test_create_tenants_conflict', body))

    @attr(kind='large')
    @tests.skip_test('Unable to create bad object')
    def test_create_tenants_bad_object(self):
        resp, body = self.client.create_tenant(True, "tenant_for_test")
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_tenants_bad_object', body))

    @attr(kind='large')
    def test_create_tenants_empty_name(self):
        resp, body = self.client.create_tenant("", "tenant_for_test")
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_tenants_empty_name', body))

    @attr(kind='large')
    @tests.skip_test('Not check 256 value in tenant name.')
    def test_create_tenants_over_256_name(self):
        resp, body = self.client.create_tenant("a" * 256, "tenant_for_test")
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_tenants_over_256_name', body))

    @attr(kind='large')
    @tests.skip_test('Not check 256 value in tenant description.')
    def test_create_tenants_over_256_description(self):
        resp, body = self.client.create_tenant("a" * 256, "tenant_for_test")
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_tenants_over_256_description', body))

    @attr(kind='large')
    def test_delete_tenants(self):
        _, body = self.client.create_tenant("test_tenant1", "tenant_for_test")
        resp, body = self.client.delete_tenant(body['tenant']['id'])
        self.assertEquals('204', resp['status'])
        messages.append(('test_delete_tenants', body))

    @attr(kind='large')
    def test_delete_tenants_with_no_grant(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.delete_tenant(tenant['id'])
        self.assertEqual('401', resp['status'])
        messages.append(('test_delete_tenants_with_no_grant',body))

    @attr(kind='large')
    def test_delete_tenants_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_tenant(user['tenantId'])
        self.assertEqual('403', resp['status'])
        messages.append(('test_delete_tenants_with_expired_user', body))

    @attr(kind='large')
    def test_delete_tenants_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_tenant(user['tenantId'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_delete_tenants_with_no_token', body))

    @attr(kind='large')
    def test_delete_tenants_with_no_exist_id(self):
        self.data.setup_one_user()
        resp, body = self.client.delete_tenant('99999999')
        self.assertEqual('404', resp['status'])
        messages.append(('test_delete_tenants_with_no_exist_id', body))

    @attr(kind='large')
    def test_auth(self):
        self.data.setup_one_user()
        # create token.
        self.token_client.auth('test_user1', 'password', 'test_tenant1')
        # reauth
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('200', resp['status'])
        messages.append(('test_auth', body))

    @attr(kind='large')
    def test_auth_with_expire_token(self):
        self.data.setup_one_user()
        # create token.
        self.token_client.auth('test_user1', 'password', 'test_tenant1')
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        self.expire_token(user['id'], tenant['id'])
        # reauth
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('200', resp['status'])
        messages.append(('test_auth_with_expire_token', body))

    @attr(kind='large')
    def test_auth_with_none_token(self):
        self.data.setup_one_user()
        # create token.
        self.token_client.auth('test_user1', 'password', 'test_tenant1')
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        self.remove_token(user['id'], tenant['id'])
        # reauth
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('200', resp['status'])
        messages.append(('test_auth_with_none_token', body))

    @attr(kind='large')
    def test_auth_with_disable_user(self):
        self.data.setup_one_user()
        self.diable_user('test_user1')
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('403', resp['status'])
        messages.append(('test_auth_with_diable_user', body))

    @attr(kind='large')
    def test_auth_with_disable_tenant(self):
        self.data.setup_one_user()
        self.diable_tenant('test_tenant1')
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('403', resp['status'])
        messages.append(('test_auth_with_disable_tenant', body))

    @attr(kind='large')
    def test_auth_with_illigal_password(self):
        self.data.setup_one_user()
        resp, body = self.token_client.auth('test_user1', 'test',
                                            'test_tenant1')
        self.assertEqual('401', resp['status'])
        messages.append(('test_auth_with_illigal_password', body))

    @attr(kind='large')
    def test_auth_with_illigal_name(self):
        self.data.setup_one_user()
        resp, body = self.token_client.auth('not_exist', 'password',
                                            'test_tenant1')
        self.assertEqual('401', resp['status'])
        messages.append(('test_auth_with_illigal_name', body))

    @attr(kind='large')
    def test_auth_with_illigal_tenant(self):
        self.data.setup_one_user()
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant99')
        self.assertEqual('401', resp['status'])
        messages.append(('test_auth_with_illigal_tenant', body))

    @attr(kind='large')
    def test_get_users(self):
        self.data.setup_one_user()
        _, body = self.client.get_users()
        users = body['users']['values']
        self.assertIn('test_user1', [u['name'] for u in users],
                        "test_user1 should be include.")

    @attr(kind='large')
    def test_get_users_with_no_grant(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.get_users()
        self.assertEqual('401', resp['status'])
        messages.append(('test_get_users_with_no_grant',body))

    @attr(kind='large')
    def test_get_users_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.get_users()
        self.assertEqual('403', resp['status'])
        messages.append(('test_get_users_with_expired_user', body))

    @attr(kind='large')
    def test_get_users_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.get_users()
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_users_with_no_token', body))

    @attr(kind='large')
    def test_create_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user2@test.com')
        self.data.users.append(body['user'])
        self.assertEqual('201', resp['status'])
        self.assertEqual('test_user2', body['user']['name'])
        messages.append(('test_create_user',body))

    @attr(kind='large')
    def test_create_users_with_no_grant(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('401', resp['status'])
        messages.append(('test_create_users_with_no_grant',body))

    @attr(kind='large')
    def test_create_users_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('403', resp['status'])
        messages.append(('test_get_users_with_expired_user', body))

    @attr(kind='large')
    def test_create_users_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_users_with_no_token', body))

    @attr(kind='large')
    def test_create_users_with_conflict_name(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user1', 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('409', resp['status'])
        messages.append(('test_create_users_with_conflict_name',body))

    @attr(kind='large')
    def test_create_users_with_conflict_email(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user1@mail.com')
        self.assertEqual('409', resp['status'])
        messages.append(('test_create_users_with_conflict_email',body))

    @attr(kind='large')
    @tests.skip_test("Not check 256 value on user name")
    def test_create_users_with_over_256_name(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('a' * 256, 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_users_with_over_256_name',body))

    @attr(kind='large')
    def test_create_users_with_empty_name(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('', 'password',
                                            tenant['id'], 'user2@test.com')
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_users_with_empty_name',body))

    @attr(kind='large')
    @tests.skip_test("Not check 256 value on user password")
    def test_create_users_with_over_256_password(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', 'p' * 256, tenant['id'], 'user2@test.com')
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_users_with_over_256_name',body))

    @attr(kind='large')
    def test_create_users_with_empty_password(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', '', tenant['id'], 'user2@test.com')
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_users_with_empty_password',body))

    @attr(kind='large')
    @tests.skip_test("Not check mail format")
    def test_create_users_with_bad_mail_format(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', 'password', tenant['id'], '12345')
        self.assertEqual('400', resp['status'])
        messages.append(('test_create_users_with_bad_mail_format',body))

    @attr(kind='large')
    def test_create_users_with_non_exist_tenant(self):
        self.data.setup_one_user()
        resp, body = self.client.create_user('test_user2', 'password', '99999999', 'user2@test.com')
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_users_with_non_exist_tenant',body))

    @attr(kind='large')
    def test_delete_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        _, body = self.client.create_user('test_user2', 'password', tenant['id'], 'user2@test.com')
        resp, body = self.client.delete_user(body['user']['id'])
        self.assertEquals('204', resp['status'])
        messages.append(('test_delete_user', body))

    @attr(kind='large')
    def test_delete_users_with_no_grant(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.delete_user(user['id'])
        self.assertEqual('401', resp['status'])
        messages.append(('test_delete_users_with_no_grant',body))

    @attr(kind='large')
    def test_delete_user_with_expired_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_user(user['id'])
        self.assertEqual('403', resp['status'])
        messages.append(('test_delete_user_with_expired_user', body))

    @attr(kind='large')
    def test_delete_user_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_user(user['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_delete_user_with_no_token', body))

    @attr(kind='large')
    def test_delete_user_with_no_exist_id(self):
        self.data.setup_one_user()
        resp, body = self.client.delete_user('99999999')
        self.assertEqual('404', resp['status'])
        messages.append(('test_delete_user_with_no_exist_id', body))

    @attr(kind='large')
    def test_get_roles(self):
        self.data.setup_role()
        _, body = self.client.get_roles()
        roles = body['roles']['values']
        role_names = [r['name'] for r in roles]
        self.assertIn(self.data.role_name, role_names)

    @attr(kind='large')
    def test_get_roles_with_no_grant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.get_roles()
        self.assertEqual('401', resp['status'])
        messages.append(('test_get_roles_with_no_grant',body))

    @attr(kind='large')
    def test_get_roles_with_expired_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.get_roles()
        self.assertEqual('403', resp['status'])
        messages.append(('test_get_roles_with_expired_user', body))

    @attr(kind='large')
    def test_get_roles_with_no_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.get_roles()
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_roles_with_no_token', body))

    @attr(kind='large')
    def test_get_user_roles(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        _, body = self.client.get_user_roles(user['id'])
        roles = body['roles']['values']
        self.assertEquals(tenant['id'], roles[0]['tenantId'])

    @attr(kind='large')
    def test_get_user_roles_with_no_grant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])

        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.get_user_roles(user['id'])
        self.assertEqual('401', resp['status'])
        messages.append(('test_get_user_roles_with_no_grant',body))

    @attr(kind='large')
    def test_get_user_roles_with_expired_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.get_user_roles(user['id'])
        self.assertEqual('403', resp['status'])
        messages.append(('test_get_user_roles_with_expired_user', body))

    @attr(kind='large')
    def test_get_user_roles_with_no_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.get_user_roles(user['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_user_roles_with_no_token', body))

    @attr(kind='large')
    def test_get_user_roles_with_not_exist_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        resp, body = self.client.get_user_roles('999999')
        self.assertEqual('404', resp['status'])
        messages.append(('test_get_user_roles_with_not_exist_user', body))

    @attr(kind='large')
    def test_create_user_roles(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        _, body = self.client.get_user_roles(user['id'])
        roles = body['roles']['values']
        self.assertEquals(tenant['id'], roles[0]['tenantId'])

    @attr(kind='large')
    def test_create_user_roles_with_no_grant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)

        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        self.assertEqual('401', resp['status'])
        messages.append(('test_create_user_roles_with_no_grant',body))

    @attr(kind='large')
    def test_create_user_roles_with_expired_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        self.assertEqual('403', resp['status'])
        messages.append(('test_create_user_roles_with_expired_user', body))

    @attr(kind='large')
    def test_create_user_roles_with_no_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_user_roles_with_no_token', body))

    @attr(kind='large')
    def test_create_user_roles_with_not_exist_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        resp, body = self.client.create_role_ref('999999', role['id'], tenant['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_user_roles_with_not_exist_user', body))

    @attr(kind='large')
    def test_create_user_roles_with_not_exist_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.create_role_ref(user['id'], '999999', tenant['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_user_roles_with_not_exist_role', body))

    @attr(kind='large')
    def test_create_user_roles_with_not_exist_tenant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        role = self.get_role_by_name(self.data.role_name)
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.create_role_ref(user['id'], role['id'], '999999')
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_user_roles_with_not_exist_user', body))

    @attr(kind='large')
    @tests.skip_test("Duplicate entry returned 500 error")
    def test_create_user_roles_with_conflict(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        resp, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        self.assertEqual('409', resp['status'])
        messages.append(('test_create_user_roles_with_conflict', body))

    @attr(kind='large')
    def test_delete_user_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        resp, body = self.client.delete_role_ref(user['id'], role['id'])
        self.assertEquals('204', resp['status'])

    @attr(kind='large')
    def test_delete_user_roles_with_no_grant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']

        self.swap_user('test_user1', 'password', 'test_tenant1')
        resp, body = self.client.delete_role_ref(user['id'], role['id'])
        self.assertEqual('401', resp['status'])
        messages.append(('test_delete_user_roles_with_no_grant',body))

    @attr(kind='large')
    def test_delete_user_roles_with_expired_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_role_ref(user['id'], role['id'])
        self.assertEqual('403', resp['status'])
        messages.append(('test_create_user_roles_with_expired_user', body))

    @attr(kind='large')
    def test_delete_user_roles_with_no_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        resp, body = self.client.delete_role_ref(user['id'], role['id'])
        self.assertEqual('404', resp['status'])
        messages.append(('test_create_user_roles_with_no_token', body))

    @attr(kind='large')
    @tests.skip_test("None exist user not occured exception")
    def test_delete_user_role_with_not_exist_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        resp, body = self.client.delete_role_ref('999999', role['id'])
        self.assertEquals('404', resp['status'])
        messages.append(('test_delete_user_role_with_not_exist_user', body))

    @attr(kind='large')
    @tests.skip_test("None exist role not occured exception")
    def test_delete_user_role_with_not_exist_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        resp, body = self.client.delete_role_ref(user['id'], '999999')
        self.assertEquals('404', resp['status'])
        messages.append(('test_delete_user_role_with_not_exist_role', body))
