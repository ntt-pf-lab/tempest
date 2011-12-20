from storm import exceptions
from storm.common import rest_client
import httplib2
import json
import storm.config


class RestClientUnauth(rest_client.RestClient):

    def keystone_v2_auth(self, user, api_key, auth_url, tenant_name):
        """
        Provides authentication via Keystone 2.0
        """

        creds = {'auth': {
                'passwordCredentials': {
                    'username': user,
                    'password': api_key,
                }
            }
        }

        if tenant_name is not None:
            creds['auth']['tenantName'] = tenant_name

        self.http_obj = httplib2.Http()
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(creds)
        resp, body = self.http_obj.request(auth_url, 'POST',
                                           headers=headers, body=body)

        try:
            auth_data = json.loads(body)['access']
            token = auth_data['token']['id']
            endpoints = auth_data['serviceCatalog'][0]['endpoints']
            mgmt_url = endpoints[0]['publicURL']

            #TODO (dwalleck): This is a horrible stopgap.
            #Need to join strings more cleanly
            temp = mgmt_url.rsplit('/')
            service_url = temp[0] + '//' + temp[2] + '/' + temp[3] + '/'
            management_url = service_url + tenant_name
            return token, management_url
        except KeyError:
            print "Failed to authenticate user"
            print resp
            print json.loads(body)
            if resp['status'] not in ('200', '202'):
                return resp['status'], ''
            return token, ''

    def request_without_token(self, method, url, headers=None, body=None):
        """A simple HTTP request interface."""

        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}
#        headers['X-Auth-Token'] = self.token

        req_url = "%s/%s" % (self.base_url, url)
        resp, body = self.http_obj.request(req_url, method,
                                           headers=headers, body=body)
        if resp['status'] != '200' and resp['status'] != '203':
            return resp, body
        body = json.loads(body)

        return resp, body

    def request_with_invalid_tenant(self, method, url, headers=None,
                                    body=None, tenant=''):
        """A simple HTTP request interface."""

        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}
        headers['X-Auth-Token'] = self.token

        req_url = "%s/%s%s" % ('/'.join(self.base_url.split('/')[:-1]), tenant,
                               url)
        resp, body = self.http_obj.request(req_url, method,
                                           headers=headers, body=body)
        if resp['status'] != '200' and resp['status'] != '203':
            return resp, body
        body = json.loads(body)

        return resp, body
