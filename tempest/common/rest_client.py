import json
import httplib2
import logging
import time
from tempest import exceptions


# redrive rate limited calls at most twice
MAX_RECURSION_DEPTH = 2


class RestClient(object):
    def __init__(self, config, user, password, auth_url, service,
                 tenant_name=None):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.ERROR)
        self.config = config
        if self.config.identity.strategy == 'keystone':
            self.token, self.base_url = self.keystone_auth(user,
                                                           password,
                                                           auth_url,
                                                           service,
                                                           tenant_name)
        else:
            self.token, self.base_url = self.basic_auth(user,
                                                        password,
                                                        auth_url)

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
        self.http_obj = httplib2.Http()
        resp, body = self._auth_token(user, password, auth_url, tenant_name)

        if resp.status == 200:
            try:
                return self._extract_auth_response(body, service)
            except KeyError:
                print "Failed to authenticate user"
                raise
        elif resp.status == 401:
            raise exceptions.AuthenticationFailure(user=user,
                                                password=password)

    def _auth_token(self, user, api_key, auth_url, tenant_name):
        creds = {'auth': {
                'passwordCredentials': {
                    'username': user,
                    'password': api_key,
                },
                'tenantName': tenant_name
            }
        }

        headers = {'Content-Type': 'application/json'}
        body = json.dumps(creds)
        rest_logging.do_auth(creds)
        resp, body = self.http_obj.request(auth_url, 'POST',
                                           headers=headers, body=body)
        return resp, body

    def _extract_auth_response(self, body, service):
        auth_data = json.loads(body)['access']
        token = auth_data['token']['id']
        tenant_id = auth_data['token']['tenant']['id']
        catalog = [s for s in auth_data['serviceCatalog']
                     if s['name'] == service]
        endpoints = catalog[0]['endpoints']
        mgmt_url = endpoints[0]['publicURL']

        #TODO (dwalleck): This is a horrible stopgap.
        #Need to join strings more cleanly
        temp = mgmt_url.rsplit('/')
        service_url = temp[0] + '//' + temp[2] + '/' + temp[3] + '/'
        #management_url = service_url + tenant_name
        management_url = service_url + tenant_id
        return token, management_url

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

        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}
        headers['X-Auth-Token'] = self.token

        req_url = "%s/%s" % (self.base_url, url)
        rest_logging.do_request(req_url, method, headers, body)
        resp, resp_body = self.http_obj.request(req_url, method,
                                           headers=headers, body=body)
        rest_logging.do_response(resp, body)

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


class RestAdminClient(RestClient):

    def _extract_auth_response(self, body, service):
        auth_data = json.loads(body)['access']
        token = auth_data['token']['id']
        catalog = [s for s in auth_data['serviceCatalog']
                     if s['name'] == service]
        endpoints = catalog[0]['endpoints']
        mgmt_url = endpoints[0]['adminURL']
        return token, mgmt_url


class RestClientLogging(object):

    def do_auth(self, creds):
        pass

    def do_request(self, req_url, method, headers, body):
        pass

    def do_response(self, resp, body):
        pass

rest_logging = RestClientLogging()
