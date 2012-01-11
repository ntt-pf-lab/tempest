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
import base64
import netaddr
import re
import subprocess
import time
import json
import logging
import inspect

import unittest2 as unittest
from nose.plugins.attrib import attr

import storm.config
from kong import tests
from storm import openstack
from storm.common import rest_client
from storm.common.rest_client import LoggingFeature
from storm.services.keystone.json.keystone_client import TokenClient
from nose.plugins import skip

#from medium.tests.processes import (
#        GlanceRegistryProcess, GlanceApiProcess,
#        KeystoneProcess,
#        QuantumProcess, QuantumPluginOvsAgentProcess,
#        NovaApiProcess, NovaComputeProcess,
#        NovaNetworkProcess, NovaSchedulerProcess)

LOG = logging.getLogger("large.tests.test_nova_manager")
messages = []


def setUpModule(module):
    pass


def tearDownModule(module):
    print "\nAll nova manage tests done."


class FunctionalTest(unittest.TestCase):

    def setUp(self):
        default_config = storm.config.StormConfig('etc/large.conf')
        self.db = DBController(default_config)
        self.config = default_config

    def tearDown(self):
        pass


class DBController(object):
    def __init__(self, config):
        self.config = config

    def exec_mysql(self, sql, database='nova'):
        LOG.debug("Execute sql %s" % sql)
        exec_sql = 'mysql -h %s -u %s -p%s %s -Ns -e "' + sql + '"'
        results = subprocess.check_output(exec_sql % (
                                          self.config.mysql.host,
                                          self.config.mysql.user,
                                          self.config.mysql.password,
                                          database),
                                          shell=True)
        LOG.debug("SQL Execution Result %s" % results)

        return [tuple(result.split('\t'))
                    for result in results.split('\n') if result]


class NovaManageTest(FunctionalTest):

    def test_network_create_with_no_uuid(self):
        # execute
        label = self._testMethodName
        fixed_range_v4 = '10.0.3.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        gateway = '10.0.3.1'
        out = subprocess.check_output('bin/nova-manage network create '
                                      '--label=%(label)s '
                                      '--fixed_range_v4=%(fixed_range_v4)s '
                                      '--num_networks=%(num_networks)s '
                                      '--network_size=%(network_size)s '
                                      '--bridge_interface=%(bridge_int)s '
                                      '--project_id=%(project_id)s '
                                      '--gateway=%(gateway)s' % locals(),
                                      cwd=self.config.nova.directory,
                                      shell=True)
        LOG.debug("out(nova-manage network create)=%s" % out)

        # assert
        sql = 'SELECT uuid FROM networks WHERE label = \'%s\';' % label
        results = self.db.exec_mysql(sql, database='nova')
        self.assertTrue(results)

    def test_network_create_with_uuid(self):
        # create L2 network for test
        tenant_id = '1'
        l2_name = 'l2_' + self._testMethodName
        out = subprocess.check_output('bin/cli create_net '
                                      '%(tenant_id)s %(l2_name)s' % locals(),
                                      cwd=self.config.quantum.directory,
                                      shell=True)
        LOG.debug("out(cli create_net)=%s" % out)

        # execute
        sql = 'SELECT uuid FROM networks WHERE name = \'%s\';' % l2_name
        uuid, = self.db.exec_mysql(sql, database='ovs_quantum')[0]
        label = self._testMethodName
        fixed_range_v4 = '10.0.4.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        out = subprocess.check_output('bin/nova-manage network create '
                                      '--label=%(label)s '
                                      '--fixed_range_v4=%(fixed_range_v4)s '
                                      '--num_networks=%(num_networks)s '
                                      '--network_size=%(network_size)s '
                                      '--bridge_interface=%(bridge_int)s '
                                      '--project_id=%(project_id)s '
                                      '--uuid=%(uuid)s'
                                      % locals(),
                                      cwd=self.config.nova.directory,
                                      shell=True)
        LOG.debug("out(nova-manage network create)=%s" % out)

        # assert
        sql = 'SELECT uuid FROM networks WHERE label = \'%s\';' % label
        results = self.db.exec_mysql(sql, database='nova')
        self.assertTrue(results)

    def test_network_create_when_cidr_is_already_used(self):
        # create a network for test
        label = self._testMethodName + '_1'
        fixed_range_v4 = '10.0.5.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        out = subprocess.check_output('bin/nova-manage network create '
                                      '--label=%(label)s '
                                      '--fixed_range_v4=%(fixed_range_v4)s '
                                      '--num_networks=%(num_networks)s '
                                      '--network_size=%(network_size)s '
                                      '--bridge_interface=%(bridge_int)s '
                                      '--project_id=%(project_id)s'
                                      % locals(),
                                      cwd=self.config.nova.directory,
                                      shell=True)
        LOG.debug("out(nova-manage network create)=%s" % out)

        # execute and assert
        label = self._testMethodName + '_2'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    def test_network_create_with_no_label(self):
        # execute and assert
        fixed_range_v4 = '10.0.6.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    @tests.skip_test('Unexpected network created')
    def test_network_create_when_label_length_is_over_255(self):
        # execute and assert
        label = 'a' * 256
        fixed_range_v4 = '10.0.7.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    def test_network_create_when_fixed_range_v4_is_not_ip_address_format(self):
        # execute and assert
        label = self._testMethodName
        fixed_range_v4 = 'xxx'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    def test_network_create_when_num_networks_is_not_one(self):
        # execute and assert
        label = self._testMethodName
        fixed_range_v4 = '10.0.8.0/24'
        num_networks = '2'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    @tests.skip_test('Unexpected network created')
    def test_network_create_when_network_size_is_greater_than_l3_block(self):
        # execute and assert
        label = self._testMethodName
        fixed_range_v4 = '10.0.9.0/24'
        num_networks = '1'
        network_size = '256'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    def test_network_create_when_network_size_is_string(self):
        # execute and assert
        label = self._testMethodName
        fixed_range_v4 = '10.0.10.0/24'
        num_networks = '1'
        network_size = 'xxx'
        bridge_int = 'br-int'
        project_id = '1'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)

    def test_network_create_when_uuid_does_not_exist(self):
        # execute and assert
        label = self._testMethodName
        fixed_range_v4 = '10.0.11.0/24'
        num_networks = '1'
        network_size = '32'
        bridge_int = 'br-int'
        project_id = '1'
        uuid = '99999999-9999-9999-9999-999999999999'
        self.assertRaises(subprocess.CalledProcessError,
                          subprocess.check_output,
                          'bin/nova-manage network create '
                          '--label=%(label)s '
                          '--fixed_range_v4=%(fixed_range_v4)s '
                          '--num_networks=%(num_networks)s '
                          '--network_size=%(network_size)s '
                          '--bridge_interface=%(bridge_int)s '
                          '--project_id=%(project_id)s '
                          '--uuid=%(uuid)s'
                          % locals(),
                          cwd=self.config.nova.directory,
                          shell=True)
