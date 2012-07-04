# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import httplib2
import logging
import time

from tempest import exceptions


# redrive rate limited calls at most twice
MAX_RECURSION_DEPTH = 2


class RestClient(object):

    def __init__(self, config, user, password, auth_url, tenant_name=None):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(getattr(logging, config.compute.log_level))
        self.config = config
        self.user = user
        self.password = password
        self.auth_url = auth_url
        self.tenant_name = tenant_name

        self.service = None
        self.token = None
        self.base_url = None
        self.tenant_id = None
        self.config = config
        self.region = 0
        self.endpoint_url = 'publicURL'
        self.strategy = self.config.identity.strategy
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}
        self.build_interval = config.compute.build_interval
        self.build_timeout = config.compute.build_timeout

    def _set_auth(self):
        """
        Sets the token and base_url used in requests based on the strategy type
        """

        if self.strategy == 'keystone':
            self.token, self.base_url = self.keystone_auth(self.user,
                                                           self.password,
                                                           self.auth_url,
                                                           self.service,
                                                           self.tenant_name)
        else:
            self.token, self.base_url = self.basic_auth(self.user,
                                                        self.password,
                                                        self.auth_url)

    def clear_auth(self):
        """
        Can be called to clear the token and base_url so that the next request
        will fetch a new token and base_url
        """

        self.token = None
        self.base_url = None

    def get_auth(self):
        """Returns the token of the current request or sets the token if
        none"""

        if not self.token:
            self._set_auth()

        return self.token

    def basic_auth(self, user, password, auth_url):
        """
        Provides authentication for the target API
        """

        params = {}
        params['headers'] = {'User-Agent': 'Test-Client', 'X-Auth-User': user,
                             'X-Auth-Key': password}

        self.http_obj = httplib2.Http()
        resp, body = self.http_obj.request(auth_url, 'GET', **params)
        try:
            return resp['x-auth-token'], resp['x-server-management-url']
        except:
            raise

    def keystone_auth(self, user, password, auth_url, service, tenant_name):
        """
        Provides authentication via Keystone
        """

        creds = {'auth': {
                'passwordCredentials': {
                    'username': user,
                    'password': password,
                },
                'tenantName': tenant_name
            }
        }

        self.http_obj = httplib2.Http()
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(creds)
        resp, body = self.http_obj.request(auth_url, 'POST',
                                           headers=headers, body=body)

        if resp.status == 200:
            try:
                auth_data = json.loads(body)['access']
                token = auth_data['token']['id']
            except Exception, e:
                print "Failed to obtain token for user: %s" % e
                raise

            mgmt_url = None
            for ep in auth_data['serviceCatalog']:
                if ep["type"] == service:
                    mgmt_url = ep['endpoints'][self.region][self.endpoint_url]
                    self.tenant_id = auth_data['token']['tenant']['id']
                    break

            if mgmt_url == None:
                raise exceptions.EndpointNotFound(service)

            if service == 'network':
                # Keystone does not return the correct endpoint for
                # quantum. Handle this separately.
                mgmt_url = mgmt_url + self.config.network.api_version + \
                             "/tenants/" + self.tenant_id

            return token, mgmt_url

        elif resp.status == 401:
            raise exceptions.AuthenticationFailure(user=user,
                                                   password=password)

    def post(self, url, body, headers):
        return self.request('POST', url, headers, body)

    def get(self, url):
        return self.request('GET', url)

    def delete(self, url):
        return self.request('DELETE', url)

    def put(self, url, body, headers):
        return self.request('PUT', url, headers, body)

    def _log(self, req_url, body, resp, resp_body):
        self.log.error('Request URL: ' + req_url)
        self.log.error('Request Body: ' + str(body))
        self.log.error('Response Headers: ' + str(resp))
        self.log.error('Response Body: ' + str(resp_body))

    def request(self, method, url, headers=None, body=None, depth=0):
        """A simple HTTP request interface."""

        if (self.token is None) or (self.base_url is None):
            self._set_auth()

        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}
        headers['X-Auth-Token'] = self.token

        req_url = "%s/%s" % (self.base_url, url)
        resp, resp_body = self.http_obj.request(req_url, method,
                                           headers=headers, body=body)
        if resp.status == 401 or resp.status == 403:
            self._log(req_url, body, resp, resp_body)
            raise exceptions.Unauthorized()

        if resp.status == 404:
            self._log(req_url, body, resp, resp_body)
            raise exceptions.NotFound(resp_body)

        if resp.status == 400:
            resp_body = json.loads(resp_body)
            self._log(req_url, body, resp, resp_body)
            raise exceptions.BadRequest(resp_body['badRequest']['message'])

        if resp.status == 409:
            resp_body = json.loads(resp_body)
            self._log(req_url, body, resp, resp_body)
            raise exceptions.Duplicate(resp_body)

        if resp.status == 413:
            resp_body = json.loads(resp_body)
            self._log(req_url, body, resp, resp_body)
            if 'overLimit' in resp_body:
                raise exceptions.OverLimit(resp_body['overLimit']['message'])
            elif depth < MAX_RECURSION_DEPTH:
                delay = resp['Retry-After'] if 'Retry-After' in resp else 60
                time.sleep(int(delay))
                return self.request(method, url, headers, body, depth + 1)
            else:
                raise exceptions.RateLimitExceeded(
                    message=resp_body['overLimitFault']['message'],
                    details=resp_body['overLimitFault']['details'])

        if resp.status in (500, 501):
            resp_body = json.loads(resp_body)
            self._log(req_url, body, resp, resp_body)
            #I'm seeing both computeFault and cloudServersFault come back.
            #Will file a bug to fix, but leave as is for now.

            if 'cloudServersFault' in resp_body:
                message = resp_body['cloudServersFault']['message']
            else:
                message = resp_body['computeFault']['message']
            raise exceptions.ComputeFault(message)

        if resp.status >= 400:
            resp_body = json.loads(resp_body)
            self._log(req_url, body, resp, resp_body)
            raise exceptions.TempestException(str(resp.status))

        return resp, resp_body

    def wait_for_resource_deletion(self, id):
        """Waits for a resource to be deleted"""
        start_time = int(time.time())
        while True:
            if self.is_resource_deleted(id):
                return
            if int(time.time()) - start_time >= self.build_timeout:
                raise exceptions.TimeoutException
            time.sleep(self.build_interval)

    def is_resource_deleted(self, id):
        """
        Subclasses override with specific deletion detection.
        """
        return False
