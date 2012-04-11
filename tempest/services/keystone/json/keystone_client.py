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


from tempest.common import rest_client
import json
import logging
import httplib2
from tempest import exceptions
from cloudfiles.fjson import json_loads
LOG = logging.getLogger("tempest.tests.identity.admin.test_identity")


class KeystoneClient(object):

    def __init__(self, config, username, password, url, tenant=None):
        self.admin_client = rest_client.RestAdminClient(config, username,
                                                        password,
                                                        url,
                                                        service="identity",
                                                        tenant_name=tenant)
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}

    def create_user(self, name, password, tenant_id, email):
        post_body = {
            'name': name,
            'password': password,
            'tenantId': tenant_id,
            'email': email
        }
        post_body = json.dumps({'user': post_body})
        resp, body = self.admin_client.post('users', post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def get_users(self):
        url = "users"
        resp, body = self.admin_client.get(url)
        body = json.loads(body)
        return resp, body

    def enable_disable_user(self, user_id, enabled):
        put_body = {
            'enabled':enabled
        }
        put_body = json.dumps({'user': put_body})
        resp, body = self.admin_client.put('users/%s/enabled' % user_id, put_body, self.headers)
        body = json.loads(body)
        return resp, body

    def delete_user(self, user_id):
        resp, body = self.admin_client.delete("users/%s" % user_id)
        return resp, body

    def create_tenant(self, name, description):
        post_body = {
            'description': description,
            'name': name
        }
        post_body = json.dumps({'tenant': post_body})
        resp, body = self.admin_client.post('tenants', post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def update_tenant(self, tenant_id, description, enabled):
        post_body = {
            'description': description,
            'enabled': enabled
        }
        post_body = json.dumps({'tenant': post_body})
        resp, body = self.admin_client.put('tenants/%s' % tenant_id, post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def get_tenants(self):
        url = "tenants"
        resp, body = self.admin_client.get(url)
        body = json.loads(body)
        return resp, body

    def delete_tenant(self, tenant_id):
        resp, body = self.admin_client.delete("tenants/%s" % tenant_id)
        return resp, body

    def get_roles(self):
        url = "OS-KSADM/roles"
        resp, body = self.admin_client.get(url)
        body = json.loads(body)
        return resp, body

    def create_role(self, name):
        post_body = {
            'name': name
        }
        post_body = json.dumps({'role': post_body})
        resp, body = self.admin_client.post(
                                    'OS-KSADM/roles', post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def delete_role(self, role_id):
        resp, body = self.admin_client.delete("OS-KSADM/roles/%s" % role_id)
        return resp, body

    def get_user_roles(self, user_id):
        resp, body = self.admin_client.get('users/%s/roleRefs' % user_id)
        body = json.loads(body)
        return resp, body

    def create_role_ref(self, user_id, role_id, tenant_id):
        post_body = {
            'roleId': role_id,
            'tenantId': tenant_id
        }
        post_body = json.dumps({'role': post_body})
        resp, body = self.admin_client.post(
                        'users/%s/roleRefs' % user_id, post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def delete_role_ref(self, user_id, role_id):
        resp, body = self.admin_client.delete('users/%s/roleRefs/%s' % (user_id, role_id))
        return resp, body

    def create_service(self, name, service_type, description):
        post_body = {
            'name': name,
            'type': service_type,
            'description': description
        }
        post_body = json.dumps({'OS_KSADM:service': post_body})
        resp, body = self.admin_client.post('OS-KSADM/services', post_body,
                                            self.headers)
        body = json.loads(body)
        return resp, body

    def get_services(self):
        url = "OS-KSADM/services"
        resp, body = self.admin_client.get(url)
        body = json.loads(body)
        return resp, body


class TokenClient(rest_client.RestClient):

    def __init__(self, config, username, password, url, tenant=None):
        self.auth_url = config.identity.auth_url

    def auth(self, user, password, tenant):
        creds = {'auth': {
                'passwordCredentials': {
                    'username': user,
                    'password': password,
                },
                'tenantName': tenant
            }
        }
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(creds)
        resp, body = self.post(self.auth_url,headers=headers, body=body)
        return resp, body

    def request(self, method, url, headers=None, body=None):
        """A simple HTTP request interface."""
        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}

        resp, resp_body = self.http_obj.request(url, method,
                                           headers=headers, body=body)


        if resp.status in (401, 403):
            resp_body = json.loads(resp_body)
            raise exceptions.Unauthorized(resp_body['error']['message'])

        return resp, resp_body

    def get_token(self, user, password, tenant):
        resp, body = self.auth(user, password, tenant)
        if resp['status'] != '202':
            body = json_loads(body)
            access = body['access']
            token = access['token']
            return token['id']
