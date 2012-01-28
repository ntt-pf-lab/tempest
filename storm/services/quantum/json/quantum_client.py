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

from storm.common import rest_client
from storm import exceptions
import json
import time
import httplib2
from cloudfiles.fjson import json_loads
from storm.common.rest_client import RestClient


class QuantumClient(object):

    def __init__(self, username, key, url, tenant, config=None):
        self.client = QuantumRestClient(username, key, url,
                                             tenant_name=tenant,
                                             config=config,
                                             service="quantum")
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}

    def list_network(self):
        resp, body = self.client.get('networks.json')
        body = json_loads(body)
        return resp, body

    def create_network(self, name, nova_id):
        post = { 
            'network': {
              'name': name,
              'nova_id': nova_id
             }
        }
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(post)
        resp, body = self.client.post('networks.json',headers=headers, body=body)
        body = json.loads(body)
        return resp, body

    def delete_network(self, uuid):
        resp, body = self.client.delete('networks/%s.json' % uuid)
        return resp, body

class QuantumRestClient(RestClient):
    
    def _extract_auth_response(self, body, service):
        auth_data = json.loads(body)['access']
        token = auth_data['token']['id']
        catalog = [s for s in auth_data['serviceCatalog']
                     if s['name'] == service]
        endpoints = catalog[0]['endpoints']
        mgmt_url = endpoints[0]['publicURL']
        return token, mgmt_url
    