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

import os
import sys
import logging
import subprocess
import MySQLdb as mdb
from contextlib import closing

import tempest.config
from tempest import exceptions
from tempest.common.ssh import Client

import novaclient.client
import glance.client

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


class GlanceDefaultClientManager(DefaultClientManager):
    """
    Manager that provides the default glance client object to access
    the OpenStack Images API
    """
    def __init__(self):
        super(GlanceDefaultClientManager, self).__init__()
        host = self.config.images.host
        port = self.config.images.port
        strategy = self.config.identity.strategy
        auth_url = self.config.identity.auth_url
        username = self.config.images.username
        password = self.config.images.password
        tenant_name = self.config.images.tenant_name

        if None in (host, port, username, password, tenant_name):
            msg = ("Missing required credentials. "
                    "host:%(host)s, port: %(port)s username: %(username)s, "
                    "password: %(password)s, "
                    "tenant_name: %(tenant_name)s") % locals()
            raise exceptions.InvalidConfiguration(msg)
        auth_url = self.config.identity.auth_url.rstrip('tokens')

        creds = {'strategy': strategy,
                 'username': username,
                 'password': password,
                 'tenant': tenant_name,
                 'auth_url': auth_url}

        # Create our default Glance client to use in testing
        self.client = glance.client.Client(host, port, creds=creds)


class WhiteBoxManager(Manager):
    """
    Manager that provides a configuration object for a test case to access
    internals of OpenStack
    """

    def __init__(self, database=None):
        super(WhiteBoxManager, self).__init__()
        self.nova_dir = self.config.compute.source_dir

    def connect_db(self, database='nova'):
        """Connect to an OpenStack MySQL database"""
        db_username = self.config.whitebox.db_username
        db_password = self.config.whitebox.db_password
        db_host = self.config.whitebox.db_host
        try:
            self.conn = mdb.connect(host=db_host, user=db_username,
                               passwd=db_password, db=database)
        except mdb.Error, e:
            raise exceptions.SQLException(message=e.args[1])

    def execute_query(self, sql, args=None, num_records=None):
        """Return one, all or no records for the formed SQL statement"""
        try:
            if isinstance(args, str):
                args = tuple([args, ])
            record_set = None
            # Extract the first word i.e operation from the sql query
            sql_op = sql.split(' ', 1)[0].upper()

            with closing(self.conn.cursor(mdb.cursors.DictCursor)) as cursor:
                cursor.execute(sql, args)

                if sql_op in ('INSERT', 'UPDATE', 'DELETE'):
                    self.conn.commit()
                if num_records == 'one':
                    record_set = cursor.fetchone()
                elif num_records == 'all':
                    record_set = cursor.fetchall()
                return record_set

        except mdb.Error, e:
            raise exceptions.SQLException(message=e.args[1])

    def nova_manage(self, category, action, params):
        """Executes nova-manage command for the given action"""
        if not(os.path.isdir(self.nova_dir)):
                sys.exit("Cannot find Nova source: %s" % self.nova_dir)

        flag_file = "--config-file=%s" % self.config.compute.config
        cmd = "bin/nova-manage %s %s %s %s" % (flag_file, category, action,
                                                    params)

        result = subprocess.check_output(cmd, cwd=self.nova_dir, shell=True)
        return result

    def get_ssh_connection(self, host, username, password):
        """Create an SSH connection object to a host"""
        ssh_timeout = self.config.compute.ssh_timeout
        ssh_client = Client(host, username, password, ssh_timeout)
        if not ssh_client.test_connection_auth():
            raise exceptions.SSHTimeout()
        else:
            return ssh_client
