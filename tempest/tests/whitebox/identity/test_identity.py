import datetime
from nose.plugins.attrib import attr
from tempest.tests.identity.base_admin_test import BaseAdminTest
from tempest.common.utils.data_utils import rand_name
from tempest import exceptions
from tempest import manager


class IdentityTest(BaseAdminTest):

    @classmethod
    def setUpClass(cls):
        super(cls, IdentityTest).setUpClass()
        cls.wb_manager = manager.WhiteBoxManager()
        cls.wb_manager.connect_db(database='keystone')

        # Set a token expires date in the past, for tests
        now = datetime.datetime.utcnow()
        past_date = now - datetime.timedelta(30)
        cls.test_expires_date = past_date.strftime("%Y-%m-%d %H:%M:%S")
        cls.token = cls.client.get_auth()

        # Get the actual expires date of current token
        sql = "SELECT expires from token where id = %s"
        result = cls.wb_manager.execute_query(sql, cls.token,
                                              num_records='one')
        cls.actual_expires_date = result['expires']

    @classmethod
    def _set_token_expiry(self, date):
        sql = "UPDATE token set expires=%s where id=%s"
        args = (date, self.token)
        self.wb_manager.execute_query(sql, args)

    #@classmethod
    def tearDown(cls):
        cls._set_token_expiry(cls.actual_expires_date)

    def expire_token(self):
        self._set_token_expiry(self.test_expires_date)

    def _get_role_params(self):
        self.data.setup_test_user()
        self.data.setup_test_role()
        user = self.get_user_by_name(self.data.test_user)
        tenant = self.get_tenant_by_name(self.data.test_tenant)
        role = self.get_role_by_name(self.data.test_role)
        return (user, tenant, role)

    @attr(type='whitebox')
    def test_create_tenant_by_user_with_expired_token(self):
        tenant_name = rand_name('test_tenant_')
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.create_tenant, tenant_name)

    @attr(type='whitebox')
    def test_delete_tenant_by_user_with_expired_token(self):
        tenant_name = rand_name('test_tenant_')
        resp, tenant = self.client.create_tenant(tenant_name)
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.delete_tenant, tenant['id'])

    @attr(type='whitebox')
    def test_list_tenant_by_user_with_expired_token(self):
        self.data.setup_test_tenant()
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized, self.client.list_tenants)

    @attr(type='whitebox')
    def test_create_user_by_user_with_expired_token(self):
        alt_user = rand_name('test_user_')
        alt_password = rand_name('pass_')
        alt_email = alt_user + '@testmail.tm'

        self.data.setup_test_tenant()
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.create_user, alt_user, alt_password,
                          self.data.tenant['id'], alt_email)

    @attr(type='whitebox')
    def test_delete_user_by_user_with_expired_token(self):
        self.data.setup_test_user()
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.delete_user,
                          self.data.user['id'])

    @attr(type='whitebox')
    def test_get_users_by_user_with_expired_token(self):
        self.data.setup_test_user()
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized, self.client.get_users)

    @attr(type='whitebox')
    def test_list_roles_with_expired_token(self):
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.list_roles)

    @attr(type='whitebox')
    def test_assign_user_role_with_expired_token(self):
        (user, tenant, role) = self._get_role_params()
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.assign_user_role, user['id'],
                          role['id'], tenant['id'])

    @attr(type='whitebox')
    def test_remove_user_role_with_exired_token(self):
        (user, tenant, role) = self._get_role_params()
        resp, user_role = self.client.assign_user_role(user['id'], role['id'],
                                                       tenant['id'])
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.remove_user_role, user['id'],
                          role['id'])

    @attr(type='whitebox')
    def test_list_user_role_with_expired_token(self):
        (user, tenant, role) = self._get_role_params()
        self.client.assign_user_role(user['id'], role['id'], tenant['id'])
        self.expire_token()
        self.assertRaises(exceptions.Unauthorized,
                          self.client.list_user_roles, user['id'])

    @attr(type='whitebox')
    def test_authentication_with_expired_token(self):
        self.data.setup_test_user()
        self.expire_token()
        resp, body = self.token_client.auth(self.data.test_user,
                                            self.data.test_password,
                                            self.data.test_tenant)
        self.assertEqual('200', resp['status'])
