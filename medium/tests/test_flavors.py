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

import subprocess

import unittest2 as unittest
from nose.plugins.attrib import attr
from nova import test
from tempest import openstack
from tempest import exceptions
import tempest.config


"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = tempest.config.TempestConfig()
config = default_config
environ_processes = []


def setUpModule(module):
    config = module.config


class FunctionalTest(unittest.TestCase):

    config = default_config
#   config2 = test_config

    def setUp(self):
        # for admin tenant
        username = config.identity.username
        password = config.identity.password
        tenant_name = config.identity.tenant_name
        self.os = openstack.Manager(username, password, tenant_name)
        # for demo tenant
        self.os2 = openstack.Manager()
        self.testing_processes = []

    def tearDown(self):
        print """

        Terminate All Instances

        """
        try:
            _, servers = self.os.servers_client.list_servers()
            print "Servers : %s" % servers
            for s in servers['servers']:
                try:
                    print "Find existing instance %s" % s['id']
                    resp, _ = self.os.servers_client.delete_server(s['id'])
                    if resp['status'] == '204' or resp['status'] == '202':
                        self.os.servers_client.wait_for_server_not_exists(
                                                                    s['id'])
                except Exception as e:
                    print e
        except Exception:
            pass
        print """

        Cleanup DB

        """

    def exec_sql(self, sql):
        exec_sql = 'mysql -u %s -p%s -h%s nova -e "' + sql + '"'
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password,
                              self.config.mysql.host),
                              shell=True)

    def get_data_from_mysql(self, sql):
        exec_sql = 'mysql -u %s -p%s -h%s nova -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.user,
                                         self.config.mysql.password,
                                         self.config.mysql.host),
                                         shell=True)

        return result


class FlavorsTest(FunctionalTest):
    # Almost same as tempest.tests.test_flavors,
    # extends MT environment behavior.

    def setUp(self):
        super(FlavorsTest, self).setUp()
        self.flavor_ref = self.config.compute.flavor_ref
        self.client = self.os.flavors_client
        self.name = 'test_flavor'
        self.ram = 512
        self.vcpus = 1
        self.disk = 10
        self.ephemeral = 10
        self.flavor_id = 1234
        self.swap = 1024
        self.rxtx = 1

    @attr(kind='medium')
    def test_list_flavors_show_all_default_flavors(self):
        """List of all flavors should contain the expected flavor"""
        _, flavors = self.client.list_flavors()
        _, flavor = self.client.get_flavor_details(self.flavor_ref)
        flavor_min_detail = {'id': flavor['id'], 'links': flavor['links'],
                             'name': flavor['name']}
        self.assertTrue(flavor_min_detail in flavors)

    @attr(kind='medium')
    def test_list_detail_flavors_show_all_default_flavors(self):
        """Detailed list of all flavors should contain the expected flavor"""

        _, flavors = self.client.list_flavors_with_detail()
        _, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertTrue(flavor in flavors)

    @attr(kind='medium')
    def test_create_flavor(self):
        """Test create flavor and newly created flavor is listed.
        This operation requires the user to have 'admin' role"""

        #Create the flavor
        resp, flavor = self.client.create_flavor(self.name, self.ram,
                                                self.vcpus, self.disk,
                                                self.ephemeral, self.flavor_id,
                                                self.swap, self.rxtx)
        self.assertEqual(200, resp.status)
        self.assertEqual(flavor['name'], self.name)
        self.assertEqual(flavor['vcpus'], self.vcpus)
        self.assertEqual(flavor['disk'], self.disk)
        self.assertEqual(flavor['ram'], self.ram)
        self.assertEqual(flavor['id'], self.flavor_id)
        self.assertEqual(flavor['swap'], self.swap)
        self.assertEqual(flavor['rxtx_factor'], self.rxtx)
        self.assertEqual(flavor['OS-FLV-EXT-DATA:ephemeral'], self.ephemeral)

        #Verify flavor is retrieved
        resp, flavor = self.client.get_flavor_details(self.flavor_id)
        self.assertEqual(resp.status, 200)
        self.assertEqual(flavor['name'], self.name)

        #Delete the flavor
        resp, body = self.client.delete_flavor(flavor['id'])
        self.assertEqual(resp.status, 202)

    @attr(kind='medium')
    def test_create_flavor_verify_entry_in_list_details(self):
        """Test create flavor and newly created flavor is listed.
        This operation requires the user to have 'admin' role"""

        #Create the flavor
        resp, flavor = self.client.create_flavor(self.name, self.ram,
                                                self.vcpus, self.disk,
                                                self.ephemeral, self.flavor_id,
                                                self.swap, self.rxtx)
        self.assertEqual(200, resp.status)
        self.assertEqual(flavor['name'], self.name)
        self.assertEqual(flavor['vcpus'], self.vcpus)
        self.assertEqual(flavor['disk'], self.disk)
        self.assertEqual(flavor['ram'], self.ram)
        self.assertEqual(flavor['id'], self.flavor_id)
        self.assertEqual(flavor['swap'], self.swap)
        self.assertEqual(flavor['rxtx_factor'], self.rxtx)
        self.assertEqual(flavor['OS-FLV-EXT-DATA:ephemeral'], self.ephemeral)

        flag = False
        #Verify flavor is retrieved
        resp, flavors = self.client.list_flavors_with_detail()
        self.assertEqual(resp.status, 200)
        for flavor in flavors:
            if flavor['name'] == self.name:
                flag = True
        self.assertTrue(flag)

        #Delete the flavor
        resp, body = self.client.delete_flavor(self.flavor_id)
        self.assertEqual(resp.status, 202)

    @attr(kind='medium')
    def test_list_flavors_when_all_flavors_deleted(self):
        """ List of all flavors should be blank"""

        # Backup list of flavors
        resp, flavors = self.client.list_flavors_with_detail()
        orig_flavors = flavors

        # Delete all flavors
        for flavor in flavors:
            self.client.delete_flavor(flavor['id'])

        resp, flavors = self.client.list_flavors()
        self.assertEqual([], flavors)

        # Re create original flavors
        for flavor in orig_flavors:
            if not flavor['swap']:
                swap = 0
            else:
                swap = flavor['swap']
            resp, _ = self.client.create_flavor(flavor['name'], flavor['ram'],
                                     flavor['vcpus'], flavor['disk'],
                                     flavor['OS-FLV-EXT-DATA:ephemeral'],
                                     flavor['id'], swap,
                                     int(flavor['rxtx_factor']))
            self.assertEqual(200, resp.status)

    @attr(kind='medium')
    def test_list_flavor_details_when_all_flavors_deleted(self):
        """Detailed List of all flavors should be blank"""

        # Backup list of flavors
        resp, flavors = self.client.list_flavors_with_detail()
        orig_flavors = flavors

        # Delete all flavors
        for flavor in flavors:
            self.client.delete_flavor(flavor['id'])

        resp, flavors = self.client.list_flavors_with_detail()
        self.assertEqual([], flavors)

        # Re create original flavors
        for flavor in orig_flavors:
            if not flavor['swap']:
                swap = 0
            else:
                swap = flavor['swap']
            resp, _ = self.client.create_flavor(flavor['name'], flavor['ram'],
                                     flavor['vcpus'], flavor['disk'],
                                     flavor['OS-FLV-EXT-DATA:ephemeral'],
                                     flavor['id'], swap,
                                     int(flavor['rxtx_factor']))
            self.assertEqual(200, resp.status)

    @test.skip_test('Skipped due to database access dependency')
    @attr(kind='medium')
    def test_list_flavors_when_delete_all_flavors_by_purge(self):
        """ List of all flavors should be blank by purge"""

        # preparing sql to remove all data from db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_flavors from db after removing all data.
        resp, flavors = self.client.list_flavors()
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @test.skip_test('Skipped due to database access dependency')
    @attr(kind='medium')
    def test_list_detail_flavors_when_delete_all_flavors_by_purge(self):
        """ Detailed list of all flavors should be blank by purge """

        # preparing sql to remove all data from db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_detail from db after removing all data.
        resp, flavors = self.client.list_flavors_with_detail()
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @test.skip_test('Skipped due to database access dependency')
    @attr(kind='medium')
    def test_list_detail_flavors_when_delete_all_flavors_by_destroy(self):
        """ Detailed list of all flavors should be blank by destroy """

        # preparing sql to marks all data as deleted.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "UPDATE instance_types SET deleted=1;")
        self.exec_sql(sql)

        # get list_detail from db after mark all data as deleted.
        resp, flavors = self.client.list_flavors_with_detail()
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @test.skip_test('Skipped due to database access dependency')
    @attr(kind='medium')
    def test_get_flavor_details_when_specify_purged_flavor(self):
        """ Return error because specified flavor is purged """

        # preparing sql to remove specific data from db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE from instance_types WHERE flavorid=3;")
        self.exec_sql(sql)

        # get flavor_detail from db after removing apecific data.
        resp, _ = self.client.get_flavor_details(3)
        self.assertEquals('404', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_get_flavor_details_raises_NotFound_for_deleted_flavor(self):
        """Return error because specified flavor is deleted"""

        # Create a test flavor
        resp, flavor = self.client.create_flavor(self.name, self.ram,
                                                self.vcpus, self.disk,
                                                self.ephemeral, 2000,
                                                self.swap, self.rxtx)

        self.assertEquals(200, resp.status)

        # Delete the flavor
        resp, _ = self.client.delete_flavor(2000)
        self.assertEqual(resp.status, 202)

        # Get deleted flavor details
        self.assertRaises(exceptions.NotFound, self.client.get_flavor_details,
                            2000)

    @attr(kind='medium')
    def test_get_flavor_details_for_invalid_flavor_id(self):
        """ Return error because way to specify is inappropriate """

        self.assertRaises(exceptions.NotFound, self.client.get_flavor_details,
                            9999)
