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


class FlavorsClient(object):

    def __init__(self, config, username, password, auth_url, tenant_name=None):
        self.config = config
        catalog_type = self.config.compute.catalog_type
        self.client = rest_client.RestClient(config, username, password,
                                             auth_url, catalog_type,
                                             tenant_name)

    def list_flavors(self, params=None):
        url = 'flavors'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "flavors?" + "".join(param_list)

        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body['flavors']

    def list_flavors_with_detail(self, params=None):
        url = 'flavors/detail'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "flavors/detail?" + "".join(param_list)

        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body['flavors']

    def get_flavor_details(self, flavor_id):
        resp, body = self.client.get("flavors/%s" % str(flavor_id))
        if resp['status'] != '200' and resp['status'] != '203':
            return resp, body
        body = json.loads(body)
        return resp, body['flavor']
