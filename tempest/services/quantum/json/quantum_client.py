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
from cloudfiles.fjson import json_loads
from tempest.common.rest_client import RestClient


class QuantumClient(object):

    def __init__(self, username, password, url, tenant, config=None):
        self.client = rest_client.RestClient(username, password, url,
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

    def detail_networks(self):
        resp, body = self.client.get('networks/detail.josn')
        body = json_loads(body)
        return resp, body

    def delete_network(self, uuid):
        resp, body = self.client.delete('networks/%s.json' % uuid)
        return resp, body

    def create_port(self, network_id, zone):
        post = {
            'port': {
                'state': 'ACTIVE',
                'nova_id': zone
            }
        }
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(post)
        resp, body = self.client.post('networks/%s/ports.json' % network_id ,headers=headers, body=body)
        body = json.loads(body)
        return resp, body

    def delete_port(self, network_id, port_id):
        resp, body = self.client.delete('networks/%s/ports/%s.json' % (network_id, port_id))
        return resp, body

    def list_ports(self, network_id):
        resp, body = self.client.get('networks/%s/ports.json' % network_id)
        body = json_loads(body)
        return resp, body

    def list_port_details(self, network_id):
        resp, body = self.client.get('networks/%s/ports/detail.json' % network_id)
        body = json_loads(body)
        return resp, body

    def attach_port(self, network_id, port_id, interface_id):
        post = {
            'attachment': {
                'id': interface_id
            }
        }
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(post)
        resp, body = self.client.put('networks/%s/ports/%s/attachment.json'
                % (network_id, port_id), headers=headers, body=body)
        return resp, body

    def detach_port(self, network_id, port_id):
        resp, body = self.client.delete('networks/%s/ports/%s/attachment.json' % (network_id, port_id))
        return resp, body

    def list_port_attachment(self, network_id, port_id):
        resp, body = self.client.get('networks/%s/ports/%s/attachment.json' % (network_id, port_id))
        body = json_loads(body)
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

