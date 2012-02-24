from storm import exceptions
import httplib2
import json
import storm.config


class RestClient(object):

    def __init__(self, user, key, auth_url, tenant_name=None, config=None,
                  service="nova"):
        if config is None:
            config = storm.config.StormConfig()
        self.config = config
        if self.config.env.authentication == 'keystone_v2':
            self.token, self.base_url = self.keystone_v2_auth(user,
                                                              key,
                                                              auth_url,
                                                              tenant_name,
                                                              service)
        else:
            self.token, self.base_url = self.basic_auth(user,
                                                        key,
                                                        auth_url)

    def basic_auth(self, user, api_key, auth_url):
        """
        Provides authentication for the target API
        """

        params = {}
        params['headers'] = {'User-Agent': 'Test-Client', 'X-Auth-User': user,
                             'X-Auth-Key': api_key}

        self.http_obj = httplib2.Http()
        resp, body = self.http_obj.request(auth_url, 'GET', **params)
        try:
            return resp['x-auth-token'], resp['x-server-management-url']
        except:
            raise

    def keystone_v2_auth(self, user, api_key, auth_url, tenant_name, service="nova"):
        """
        Provides authentication via Keystone 2.0
        """
        self.http_obj = httplib2.Http()
        resp, body = self._auth_token(user, api_key, auth_url, tenant_name)

        try:
            return self._extract_auth_response(body, service)
        except KeyError:
            print "Failed to authenticate user"
            raise

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
        logging.do_auth(creds)
        resp, body = self.http_obj.request(auth_url, 'POST',
                                           headers=headers, body=body)
#        logging.do_response(resp, body)
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
#            management_url = service_url + tenant_name
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

    def request(self, method, url, headers=None, body=None):
        """A simple HTTP request interface."""

        self.http_obj = httplib2.Http()
        if headers == None:
            headers = {}
        headers['X-Auth-Token'] = self.token

        req_url = "%s/%s" % (self.base_url, url)
        logging.do_request(req_url, method, headers, body)
        resp, body = self.http_obj.request(req_url, method,
                                           headers=headers, body=body)
        logging.do_response(resp, body)
#        if resp.status == 400:
#            body = json.loads(body)
#            raise exceptions.BadRequest(body['badRequest']['message'])

        return resp, body


class RestAdminClient(RestClient):

    def _extract_auth_response(self, body, service):
        auth_data = json.loads(body)['access']
        token = auth_data['token']['id']
        catalog = [s for s in auth_data['serviceCatalog']
                     if s['name'] == service]
        endpoints = catalog[0]['endpoints']
        mgmt_url = endpoints[0]['adminURL']
        return token, mgmt_url

class LoggingFeature(object):

    def do_auth(self, creds):
        pass

    def do_request(self, req_url, method, headers, body):
        pass

    def do_response(self, resp, body):
        pass

logging = LoggingFeature()
