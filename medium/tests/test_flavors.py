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
import time

import unittest2 as unittest
from nose.plugins.attrib import attr
from nova import test
from storm import openstack
import storm.config


"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

# for admin tenant
default_config = storm.config.StormConfig('etc/medium.conf')
# for demo tenant
test_config = storm.config.StormConfig('etc/medium_test.conf')
config = default_config
environ_processes = []


def setUpModule(module):
    config = module.config


class FunctionalTest(unittest.TestCase):

    config = default_config
    config2 = test_config

    def setUp(self):
        # for admin tenant
        self.os = openstack.Manager(config=self.config)
        # for demo tenant
        self.os2 = openstack.Manager(config=self.config2)
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
    # Almost same as storm.tests.test_flavors,
    # extends MT environment behavior.

    def setUp(self):
        super(FlavorsTest, self).setUp()
        self.flavor_ref = self.config.env.flavor_ref
        self.client = self.os.flavors_client

    @attr(kind='medium')
    def test_list_flavors_show_all_default_flavors(self):
        """ List of all flavors should contain the expected flavor """
        _, body = self.client.list_flavors()
        flavors = body['flavors']
        _, flavor = self.client.get_flavor_details(self.flavor_ref)
        flavor_min_detail = {'id': flavor['id'], 'links': flavor['links'],
                             'name': flavor['name']}
        self.assertTrue(flavor_min_detail in flavors)

    @attr(kind='medium')
    def test_list_flavors_when_list_is_blank(self):
        """ List of all flavors should be blank"""

        # preparing sql to blank db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_flavors from blank db.
        resp, body = self.client.list_flavors()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;")
        self.exec_sql(sql)
        sql = ("DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_flavors_when_add_new_flavor(self):
        """ List of all flavors should contain the expected new flavor """

        # preparing sql to add new data to db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;")
        self.exec_sql(sql)
        time.sleep(5)
        sql = ("INSERT INTO instance_types "
                "(deleted, name, memory_mb, vcpus, local_gb, flavorid) "
                "VALUES (0, 'm1.opst', 512, 2, 20, 6);")
        self.exec_sql(sql)

        # get list_flavors from db after added new data.
        resp, body = self.client.list_flavors()
        flavors = body['flavors']
        self.flg = False
        for i in range(0, 5):
            if 'm1.opst' in body['flavors'][i]['name']:
                self.flg = True
        self.assertEquals('200', resp['status'])
        self.assertTrue(self.flg)

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_flavors_when_delete_all_flavors_by_purge(self):
        """ List of all flavors should be blank by purge"""

        # preparing sql to remove all data from db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_flavors from db after removing all data.
        resp, body = self.client.list_flavors()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_flavors_when_delete_all_flavors_by_destroy(self):
        """ List of all flavors should be blank by destroy"""

        # preparing sql to marks all data as deleted.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "UPDATE instance_types SET deleted=1;")
        self.exec_sql(sql)

        # get list_flavors from db after mark all data as deleted.
        resp, body = self.client.list_flavors()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_flavors_when_specify_get_parameter(self):
        """ List of all flavors match with specified GET parameter"""

        resp, body = self.client.list_flavors(
                                        {'minDisk': 'aaa', 'minRam': 'bbb'})
        print "resp=", resp
        print "body=", body

    @attr(kind='medium')
    def test_list_flavors_when_specify_invalid_get_parameter(self):
        """ List of all flavors match with specified GET parameter"""

        resp, body = self.client.list_flavors({'aaa': 80, 'bbb': 8192})
        print "resp=", resp
        print "body=", body

    @attr(kind='medium')
    def test_list_detail_flavors_show_all_default_flavors(self):
        """ Detailed list of all flavors should contain the expected flavor """

        _, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        _, flavor = self.client.get_flavor_details(self.flavor_ref)
        self.assertTrue(flavor in flavors)

    @attr(kind='medium')
    def test_list_detail_flavors_when_list_is_blank(self):
        """ Detailed list of all flavors should be blank """

        # preparing sql to blank db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_detail from blank db.
        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;")
        self.exec_sql(sql)
        sql = ("DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_detail_flavors_when_add_new_flavor(self):
        """ Detailed list of all flavors
                                     should contain the expected new flavor """

        # preparing sql to add new data to db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;")
        self.exec_sql(sql)
        time.sleep(5)
        sql = ("INSERT INTO instance_types "
                "(deleted, name, memory_mb, vcpus, local_gb, flavorid) "
                "VALUES (0, 'm1.opst', 512, 2, 20, 6);")
        self.exec_sql(sql)

        # get list_detail from db after added new data.
        _, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        self.flag = False
        for i in range(0, 5):
            if 'm1.opst' in body['flavors'][i]['name']:
                self.flag = True
        self.assertTrue(self.flag)

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_detail_flavors_when_delete_all_flavors_by_purge(self):
        """ Detailed list of all flavors should be blank by purge """

        # preparing sql to remove all data from db.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "DELETE FROM instance_types;")
        self.exec_sql(sql)

        # get list_detail from db after removing all data.
        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_list_detail_flavors_when_delete_all_flavors_by_destroy(self):
        """ Detailed list of all flavors should be blank by destroy """

        # preparing sql to marks all data as deleted.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "UPDATE instance_types SET deleted=1;")
        self.exec_sql(sql)

        # get list_detail from db after mark all data as deleted.
        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        self.assertEquals([], flavors)
        self.assertEquals('200', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(type='smoke')
    def test_get_flavor_details_when_flavor_exists(self):
        """ The expected flavor details should be returned """
        _, flavor = self.client.get_flavor_details(1)
        self.assertEqual(self.flavor_ref, flavor['id'])

    @attr(kind='medium')
    def test_get_flavor_details_when_flavor_not_exist(self):
        """ Return error because specified flavor does not exist """
        resp, _ = self.client.get_flavor_details(10)
        self.assertEquals('404', resp['status'])

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

    @test.skip_test('Skip this case for bug #422')
    @attr(kind='medium')
    def test_get_flavor_details_when_specify_destroyed_flavor(self):
        """ Return error because specified flavor is destroyed """

        # preparing sql to marks specific data as deleted.
        sql = ("CREATE TABLE instance_types_bk LIKE instance_types;"
               "INSERT INTO instance_types_bk SELECT * FROM instance_types;"
               "UPDATE instance_types SET deleted=1 WHERE flavorid=3;")
        self.exec_sql(sql)

        # get flavor_detail from db after mark specific data as deleted.
        resp, _ = self.client.get_flavor_details(3)
        self.assertEquals('404', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

    @attr(kind='medium')
    def test_get_flavor_details_when_specify_invalid_id(self):
        """ Return error because way to specify is inappropriate """

        # get flavor_detail from db after mark specific data as deleted.
        resp, _ = self.client.get_flavor_details('test_opst')
        self.assertEquals('400', resp['status'])
