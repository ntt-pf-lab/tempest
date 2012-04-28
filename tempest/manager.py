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

import logging
import time

import novaclient.client
import unittest2 as unittest

import tempest.config
from tempest import exceptions

LOG = logging.getLogger(__name__)


class Manager(object):

    """
    Base manager class

    Manager objects are responsible for providing a configuration object
    and a client object for a test case to use in performing actions.
    """

    def __init__(self):
        self.config = tempest.config.TempestConfig()
        self.client = None


class DefaultClientManager(Manager):

    """
    Manager class that indicates the client provided by the manager
    is the default Python client that an OpenStack API provides.
    """
    pass


class FuzzClientManager(Manager):

    """
    Manager class that indicates the client provided by the manager
    is a fuzz-testing client that Tempest contains. These fuzz-testing
    clients are used to be able to throw random or invalid data at
    an endpoint and check for appropriate error messages returned
    from the endpoint.
    """
    pass


class ComputeDefaultClientManager(DefaultClientManager):
    
    """
    Manager that provides the default python-novaclient client object
    to access the OpenStack Compute API.
    """

    NOVACLIENT_VERSION = '2'

    def __init__(self):
        super(ComputeDefaultClientManager, self).__init__()
        username = self.config.compute.username
        password = self.config.compute.password
        tenant_name = self.config.compute.tenant_name

        if None in (username, password, tenant_name):
            msg = ("Missing required credentials. "
                   "username: %(username)s, password: %(password)s, "
                   "tenant_name: %(tenant_name)s") % locals()
            raise exceptions.InvalidConfiguration(msg)

        # Novaclient adds a /tokens/ part to the auth URL automatically
        auth_url = self.config.identity.auth_url.rstrip('tokens')

        client_args = (username, password, tenant_name, auth_url)

        # Create our default Nova client to use in testing
        self.client = novaclient.client.Client(self.NOVACLIENT_VERSION,
                        *client_args,
                        service_type=self.config.compute.catalog_type)
