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
import unittest2 as unittest
from nose.plugins.attrib import attr

from tempest import openstack
from tempest.common.utils.data_utils import rand_name
import tempest.config
from tempest import exceptions


class FunctionalTest(unittest.TestCase):

    def setUp(self):
        self.os = openstack.AdminManager()
        self.client = self.os.keystone_client
        self.token_client = self.os.tokens_client
        self.data = DataGenerator(self.client)
        self.config = tempest.config.TempestConfig()
        self.db = DBController(self.config)

    def tearDown(self):
        self.data.teardown_all()

    @attr(kind='large')
    def swap_user(self, user, password, tenant_name):
        '''Recreate client object for different user'''
        self.config.compute_admin.conf.set('compute-admin', 'username', user)
        self.config.compute_admin.conf.set('compute-admin', 'password',
                                            password)
        self.config.compute_admin.conf.set('compute-admin', 'tenant_name',
                                            tenant_name)
        self.os = openstack.Manager()
        self.client = self.os.keystone_client

    @attr(kind='large')
    def disable_user(self, user_name):
        user = self.get_user_by_name(user_name)
        self.client.enable_disable_user(user['id'], False)

    @attr(kind='large')
    def disable_tenant(self, tenant_name):
        tenant = self.get_tenant_by_name(tenant_name)
        self.client.update_tenant(tenant['id'], tenant['description'], False)

    @attr(kind='large')
    def get_user_by_name(self, name):
        _, body = self.client.get_users()
        users = body['users']
        user = [u for u in users if u['name'] == name]
        if len(user) > 0:
            return user[0]

    @attr(kind='large')
    def get_tenant_by_name(self, name):
        _, body = self.client.get_tenants()
        tenants = body['tenants']
        tenant = [t for t in tenants if t['name'] == name]
        if len(tenant) > 0:
            return tenant[0]

    @attr(kind='large')
    def get_role_by_name(self, name):
        _, body = self.client.get_roles()
        roles = body['roles']
        role = [r for r in roles if r['name'] == name]
        if len(role) > 0:
            return role[0]

    @attr(kind='large')
    def expire_token(self, user_id, tenant_id):
        sql = "update token set expires = '2000-01-01' where extra like \
        '%\"user\"%\"id\"=\%\"%s\"% \
                tenant_id=%s" % (user_id, tenant_id)
        self.db.exec_mysql(sql)

    @attr(kind='large')
    def remove_token(self, user_id, tenant_id):
        sql = "delete from token where extra like '%\"user\"%\"id\": \
            \"%s\"%\"tenantId\": \"%s\"'" % \
                (user_id, tenant_id)
        self.db.exec_mysql(sql)


class DBController(object):
    def __init__(self, config):
        self.config = config

    def exec_mysql(self, sql):
        exec_sql = 'mysql -h %s -u %s -p%s keystone -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.host,
                                         self.config.mysql.user,
                                         self.config.mysql.password),
                                         shell=True)


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
        self.role_name = rand_name('role')
        _, roles = self.client.create_role(self.role_name)
        self.roles.append(roles['role'])

    def teardown_all(self):
        for u in self.users:
            self.client.delete_user(u['id'])
        for t in self.tenants:
            self.client.delete_tenant(t['id'])
        for r in self.roles:
            self.client.delete_role(r['id'])


class IdentityAdminTest(FunctionalTest):

    @attr(kind='large')
    def test_get_tenants(self):
        self.data.setup_one_user()
        _, body = self.client.get_tenants()
        tenants = body['tenants']
        self.assertIn('admin', [t['name'] for t in tenants],
                        "test_tenant1 should be include.")

    @attr(kind='large')
    def test_get_tenants_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.get_tenants)

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_tenants_by_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.get_tenants)

    @attr(kind='large')
    #@unittest.skip("devstack")
    def test_get_tenants_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.get_tenants)

    @attr(kind='large')
    def test_create_tenant(self):
        _, body = self.client.create_tenant("test_tenant1", "tenant_for_test")
        self.data.tenants.append(body['tenant'])
        self.assertEquals('test_tenant1', body['tenant']['name'])
        self.assertEquals('tenant_for_test', body['tenant']['description'])

    @attr(kind='large')
    def test_create_tenant_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.create_tenant,
                        "test_no_grant", "not created")

    @attr(kind='large')
#    @unittest.skip("devstack")
    def test_create_tenant_by_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        #self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.create_tenant,
                        'test_expired', 'not created')

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_tenant_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.create_tenant,
                            'test_no_token', 'not_created')

    @attr(kind='large')
    def test_create_tenant_with_duplicate_name(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.Duplicate, self.client.create_tenant,
                            "test_tenant1", "tenant_for_test")

    @attr(kind='large')
    @unittest.skip('Unable to create bad object')
    def test_create_tenant_bad_object(self):
        self.assertRaises(exceptions.BadRequest, self.client.create_tenant,
                            True, "tenant_for_test")

    @attr(kind='large')
    @unittest.skip("Skipping due to FAIL: BadRequest not raised")
    def test_create_tenant_empty_name(self):
        self.assertRaises(exceptions.BadRequest, self.client.create_tenant, "",
                "tenant_for_test")

    @attr(kind='large')
    @unittest.skip('Skipping until Bug #966249 is fixed')
    def test_create_tenant_name_length_over_64(self):
        self.assertRaises(exceptions.BadRequest, self.client.create_tenant,
                            "a" * 64, "tenant_for_test")

    @attr(kind='large')
    def test_delete_tenant(self):
        _, body = self.client.create_tenant("test_tenant1", "tenant_for_test")
        resp, body = self.client.delete_tenant(body['tenant']['id'])
        self.assertEquals('204', resp['status'])

    @attr(kind='large')
    def test_delete_tenant_by_unauthorized_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.delete_tenant,
                            tenant['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_tenant_by_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.delete_tenant,
                        user['tenantId'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_tenant_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.delete_tenant,
                            user['tenantId'])

    @attr(kind='large')
    def test_delete_non_existant_tenant(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.NotFound, self.client.delete_tenant,
                            '99999999abc')

    @attr(kind='large')
    def test_user_authentication(self):
        self.data.setup_one_user()
        # create token.
        self.token_client.auth('test_user1', 'password', 'test_tenant1')
        # reauth
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertEqual('200', resp['status'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_authentication_with_expired_token(self):
        self.data.setup_one_user()
        # create token.
        self.token_client.auth('test_user1', 'password', 'test_tenant1')
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        self.expire_token(user['id'], tenant['id'])
        # reauth
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                            'test_user1', 'password','test_tenant1')

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_authentication_without_any_token(self):
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

    @attr(kind='large')
    def test_authentication_for_disabled_user(self):
        self.data.setup_one_user()
        self.disable_user('test_user1')
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                            'test_user1', 'password', 'test_tenant1')

    @attr(kind='large')
    def test_authentication_when_tenant_is_disabled(self):
        self.data.setup_one_user()
        self.disable_tenant('test_tenant1')
        resp, body = self.token_client.auth('test_user1', 'password',
                                            'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                          'test_user1', 'password', 'test_tenant1')

    @attr(kind='large')
    def test_authentication_with_invalid_username(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                            'junkname1234', 'password', 'test_tenant1')

    @attr(kind='large')
    def test_authentication_with_invalid_password(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                            'test_user1', 'junkpass1234', 'test_tenant1')

    @attr(kind='large')
    def test_authentication_with_invalid_tenant(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.Unauthorized, self.token_client.auth,
                            'test_user1', 'password', 'junktenant1234')

    @attr(kind='large')
    def test_get_users(self):
        self.data.setup_one_user()
        _, body = self.client.get_users()
        users = body['users']
        self.assertIn('test_user1', [u['name'] for u in users],
                        "test_user1 should be include.")

    @attr(kind='large')
    def test_get_users_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.get_users)

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_users_by_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.get_users)

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_users_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.get_users)

    @attr(kind='large')
    def test_create_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        resp, body = self.client.create_user('test_user2', 'password',
                                            tenant['id'], 'user2@test.com')
        self.data.users.append(body['user'])
        self.assertEqual('200', resp['status'])
        self.assertEqual('test_user2', body['user']['name'])

    @attr(kind='large')
    def test_create_user_by_unauthorized_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.create_user
                            ,'test_user2', 'password', tenant['id'],
                            'user2@test.com')

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.create_user,
                            'test_user2', 'password', tenant['id'],
                            'user2@test.com')

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.create_user,
                            'test_user2', 'password', tenant['id'],
                            'user2@test.com')

    @attr(kind='large')
    def test_create_user_with_duplicate_name(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.assertRaises(exceptions.Duplicate, self.client.create_user,
                                            'test_user1',
                                            'password',
                                            tenant['id'],
                                            'user2@test.com')

    @attr(kind='large')
    @unittest.skip('Skipping until Bug #966249 is fixed')
    def test_create_user_with_name_length_over_64(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.assertRaises(exceptions.BadRequest, self.client.create_user,
                            'a' * 64, 'password', tenant['id'],
                            'user2@test.com')

    @attr(kind='large')
    def test_create_user_with_empty_name(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.assertRaises(exceptions.BadRequest, self.client.create_user,
                            '', 'password', tenant['id'], 'user2@test.com')

    @attr(kind='large')
    def test_create_user_with_empty_password(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.assertRaises(exceptions.BadRequest, self.client.create_user,
                        'test_user2', '', tenant['id'], 'user2@test.com')

    @attr(kind='large')
    @unittest.skip("Skipped: Does not validate e-mail format")
    def test_create_user_with_invalid_email_format(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        self.assertRaises(exceptions.BadRequest, self.client.create_user,
                        'test_user2', 'password', tenant['id'], '12345')

    @attr(kind='large')
    def test_create_user_for_non_existant_tenant(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.NotFound, self.client.create_user,
                            'test_user2', 'password', '9999999abc',
                            'user2@test.com')

    @attr(kind='large')
    def test_delete_user(self):
        self.data.setup_one_user()
        tenant = self.get_tenant_by_name('test_tenant1')
        _, body = self.client.create_user('test_user2', 'password', tenant['id'], 'user2@test.com')
        resp, body = self.client.delete_user(body['user']['id'])
        self.assertEquals('204', resp['status'])

    @attr(kind='large')
    def test_delete_users_by_unauthorized_user(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.delete_user,
                            user['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_user_by_user_with_expired_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_tenants()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.delete_user,
                            user['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_user_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        # maybe gone well.
        self.client.get_tenants()
        self.remove_token(user['id'], user['tenantId'])
        self.assertEqual(exceptions.NotFound, self.client.delete_user,
                        user['id'])

    @attr(kind='large')
    def test_delete_non_existant_user(self):
        self.data.setup_one_user()
        self.assertRaises(exceptions.NotFound, self.client.delete_user,
                            '99999999')

    @attr(kind='large')
    def test_get_role(self):
        self.data.setup_role()
        _, body = self.client.get_roles()
        roles = body['roles']
        role_names = [r['name'] for r in roles]
        self.assertIn(self.data.role_name, role_names)

    @attr(kind='large')
    def test_get_role_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.get_roles)

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_role_with_expired_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.get_roles)

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_role_request_without_token(self):
        self.data.setup_one_user()
        user = self.get_user_by_name('test_user1')
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.get_roles)

    @attr(kind='large')
    def test_get_user_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        _, body = self.client.get_user_roles(user['id'])
        roles = body['roles']
        self.assertEquals(tenant['id'], roles[0]['tenantId'])

    @attr(kind='large')
    def test_get_user_role_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])

        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.get_user_roles,
                        user['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_user_role_with_expired_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized, self.client.get_user_roles,
                            user['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_get_user_role_request_without_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.get_user_roles,
                            user['id'])

    @attr(kind='large')
    @unittest.skip("Skipped: NotFound not raised for non existant user")
    def test_get_user_role_non_existant_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        # create a new token for test_user1.
        self.assertRaises(exceptions.NotFound, self.client.get_user_roles,
                        '999999abc')

    @attr(kind='large')
    def test_create_user_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        _, body = self.client.get_user_roles(user['id'])
        roles = body['roles']
        self.assertEquals(tenant['id'], roles[0]['tenantId'])

    @attr(kind='large')
    def test_create_user_role_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.create_role_ref,
                          user['id'], role['id'], tenant['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_role_with_expired_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.Unauthorized,
                        self.client.create_role_ref, user['id'], role['id'],
                        tenant['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_role_request_without_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.create_role_ref,
                            user['id'], role['id'], tenant['id'])

    @attr(kind='large')
    def test_create_user_role_non_existant_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.assertRaises(exceptions.NotFound, self.client.create_role_ref,
                            '999999', role['id'], tenant['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_role_non_existant_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.create_role_ref,
                            user['id'], '999999', tenant['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_create_user_role_non_existant_tenant(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        role = self.get_role_by_name(self.data.role_name)
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NontFound, self.client.create_role_ref,
                            user['id'], role['id'], '999999')

    @attr(kind='large')
    @unittest.skip("Skipped: AssertionError: Duplicate not raised")
    def test_create_user_role_duplicate_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        self.assertRaises(exceptions.Duplicate, self.client.create_role_ref,
                            user['id'], role['id'], tenant['id'])

    @attr(kind='large')
    @unittest.skip("Skipped: 500 Internal Server Error")
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
    def test_delete_user_role_by_unauthorized_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'],
                                                tenant['id'])
        role = body['role']
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.assertRaises(exceptions.Unauthorized, self.client.delete_role_ref,
                                                    user['id'], role['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_user_role_with_expired_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.expire_token(user['id'], user['tenantId'])
        self.assertRaises(self.client.delete_role_ref,
                            user['id'], role['id'])

    @attr(kind='large')
    @unittest.skip("devstack")
    def test_delete_user_role_request_without_token(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        # create a new token for test_user1.
        self.swap_user('test_user1', 'password', 'test_tenant1')
        self.client.get_users()
        self.remove_token(user['id'], user['tenantId'])
        self.assertRaises(exceptions.NotFound, self.client.delete_role_ref,
                            user['id'], role['id'])

    @attr(kind='large')
    @unittest.skip("Skipped: 500 Internal Server Error")
    def test_delete_user_role_non_existant_user(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        self.assertRaises(exceptions.NotFound, self.client.delete_role_ref,
                                    '999999abc', role['id'])

    @attr(kind='large')
    @unittest.skip("Skipped: 500 Internal Server Error")
    def test_delete_user_role_non_existant_role(self):
        self.data.setup_one_user()
        self.data.setup_role()
        user = self.get_user_by_name('test_user1')
        tenant = self.get_tenant_by_name('test_tenant1')
        role = self.get_role_by_name(self.data.role_name)
        _, body = self.client.create_role_ref(user['id'], role['id'], tenant['id'])
        role = body['role']
        self.assertRaises(exceptions.NotFound, self.client.delete_role_ref,
                            user['id'], '999999abc')
