import base64
import re
import subprocess
import time

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name

from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        NovaApiProcess, NovaComputeProcess,
        NovaNetworkProcess, NovaSchedulerProcess)
from medium.tests.utils import (
        emphasised_print, silent_check_call,
        cleanup_virtual_instances, cleanup_processes)

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""

default_config = storm.config.StormConfig('etc/medium.conf')
config = default_config
environ_processes = []


def setUpModule(module):
    environ_processes = module.environ_processes
    config = module.config

    # glance.
    environ_processes.append(GlanceRegistryProcess(
            config.glance.directory,
            config.glance.registry_config))
    environ_processes.append(GlanceApiProcess(
            config.glance.directory,
            config.glance.api_config,
            config.glance.host,
            config.glance.port))

    # keystone.
    environ_processes.append(KeystoneProcess(
            config.keystone.directory,
            config.keystone.config,
            config.keystone.host,
            config.keystone.port))

    # quantum.
    environ_processes.append(QuantumProcess(
        config.quantum.directory,
        config.quantum.config))
    environ_processes.append(QuantumPluginOvsAgentProcess(
        config.quantum.directory,
        config.quantum.agent_config))

    for process in environ_processes:
        process.start()
    time.sleep(10)


def tearDownModule(module):
    for process in module.environ_processes:
        process.stop()
    del module.environ_processes[:]


class FunctionalTest(unittest.TestCase):

    config = default_config

    def setUp(self):
        self.os = openstack.Manager(config=self.config)
        self.testing_processes = []

        # nova.
        self.testing_processes.append(NovaApiProcess(
                self.config.nova.directory,
                self.config.nova.host,
                self.config.nova.port))
        self.testing_processes.append(NovaComputeProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaNetworkProcess(
                self.config.nova.directory))
        self.testing_processes.append(NovaSchedulerProcess(
                self.config.nova.directory))

#        reset db.
        subprocess.check_call('mysql -uroot -pnova -e "'
                              'DROP DATABASE IF EXISTS nova;'
                              'CREATE DATABASE nova;'
                              '"',
                              shell=True)
        subprocess.call(['bin/nova-manage', 'db', 'sync'],
                        cwd=self.config.nova.directory)

        for process in self.testing_processes:
            process.start()
        time.sleep(10)

    def tearDown(self):
        # kill still existing virtual instances.
        for line in subprocess.check_output('virsh list --all',
                                            shell=True).split('\n')[2:-2]:
            (id, name, state) = line.split()
            if state == 'running':
                subprocess.check_call('virsh destroy %s' % id, shell=True)
            subprocess.check_call('virsh undefine %s' % name, shell=True)

        for process in self.testing_processes:
            process.stop()
        del self.testing_processes[:]

    def exec_sql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -e "' + sql + '"'
        subprocess.check_call(exec_sql % (
                              self.config.mysql.user,
                              self.config.mysql.password),
                              shell=True)

    def get_data_from_mysql(self, sql):
        exec_sql = 'mysql -u %s -p%s nova -Ns -e "' + sql + '"'
        result = subprocess.check_output(exec_sql % (
                                         self.config.mysql.user,
                                         self.config.mysql.password),
                                         shell=True)


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
        resp, body = self.client.list_flavors()
        flavors = body['flavors']
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
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

        resp, body = self.client.list_flavors({'minDisk':'aaa', 'minRam':'bbb'})
        print "resp=", resp
        print "body=", body

    @attr(kind='medium')
    def test_list_flavors_when_specify_invalid_get_parameter(self):
        """ List of all flavors match with specified GET parameter"""

        resp, body = self.client.list_flavors({'aaa':80, 'bbb':8192})
        print "resp=", resp
        print "body=", body


    @attr(kind='medium')
    def test_list_detail_flavors_show_all_default_flavors(self):
        """ Detailed list of all flavors should contain the expected flavor """

        resp, body = self.client.list_flavors_with_detail()
        flavors = body['flavors']
        resp, flavor = self.client.get_flavor_details(self.flavor_ref)
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
        resp, body = self.client.list_flavors_with_detail()
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
        resp, flavor = self.client.get_flavor_details(1)
        self.assertEqual(self.flavor_ref, flavor['id'])

    @attr(kind='medium')
    def test_get_flavor_details_when_flavor_not_exist(self):
        """ Return error because specified flavor does not exist """
        resp, flavor = self.client.get_flavor_details(10)
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
        resp, flavor = self.client.get_flavor_details(3)
        self.assertEquals('404', resp['status'])

        # initialize db correctly.
        sql = ("TRUNCATE table instance_types;"
               "INSERT INTO instance_types SELECT * FROM instance_types_bk;"
               "DROP TABLE IF EXISTS instance_types_bk;")
        self.exec_sql(sql)

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
        self.assertEquals('200', resp['status'])

    @attr(kind='medium')
    def test_get_flavor_details_when_specify_invalid_id(self):
        """ Return error because way to specify is inappropriate """

        # get flavor_detail from db after mark specific data as deleted.
        resp, flavor = self.client.get_flavor_details('test_opst')
        self.assertEquals('404', resp['status'])