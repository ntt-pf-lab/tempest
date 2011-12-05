import base64
import os
import re
import subprocess
import time
import urllib

import unittest2 as unittest
from nose.plugins.attrib import attr

from storm import exceptions
from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name

"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""


def wait_to_launch(host, port):
    while True:
        try:
            urllib.urlopen('http://%(host)s:%(port)s/' % locals())
            time.sleep(.1)
            break
        except IOError:
            pass


def kill_children_process(pid, force=False):
    pid = int(pid)
    for line in subprocess.check_output(
            '/bin/ps -eo "ppid pid"',
            shell=True).split('\n')[1:]:
        line = line.strip()
        if line:
            ppid, child_pid = line.split()
            ppid = int(ppid)
            child_pid = int(child_pid)
            if ppid == pid:
                kill_children_process(child_pid, force=force)
                if force:
                    os.system('/usr/bin/sudo /bin/kill %d' % child_pid)
                else:
                    os.system('/bin/kill %d' % child_pid)


class Process(object):
    def __init__(self, cwd, command):
        self._process = None
        self.cwd = cwd
        self.command = command

    def start(self):
        self._process = subprocess.Popen(self.command,
                                         cwd=self.cwd)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class GlanceRegistryProcess(Process):
    def __init__(self, directory, config):
        super(GlanceRegistryProcess, self)\
                .__init__(directory,
                          ["bin/glance-registry",
                           "--config-file=%s" % config])


class GlanceApiProcess(Process):
    def __init__(self, directory, config, host, port):
        super(GlanceApiProcess, self)\
                .__init__(directory,
                          ["bin/glance-api",
                           "--config-file=%s" % config])
        self.host = host
        self.port = port

    def start(self):
        super(GlanceApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class KeystoneProcess(Process):
    def __init__(self, directory, config, host, port):
        super(KeystoneProcess, self)\
                .__init__(directory,
                          ["bin/keystone",
                           "--config-file", config,
                           "-d"])
        self.host = host
        self.port = port

    def start(self):
        super(KeystoneProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaProcess(Process):
    lock_path = '/tmp/nova_locks'

    def __init__(self, cwd, command):
        command = list(command)
        command.append('--lock_path=%s' % self.lock_path)
        super(NovaProcess, self)\
                .__init__(cwd, command)

    def start(self):
        subprocess.check_call('mkdir -p %s' % self.lock_path, shell=True)
        super(NovaProcess, self).start()

    def stop(self):
        super(NovaProcess, self).stop()
        subprocess.check_call('rm -rf %s' % self.lock_path, shell=True)


class NovaApiProcess(NovaProcess):
    def __init__(self, directory, host, port):
        super(NovaApiProcess, self)\
                .__init__(directory, ["bin/nova-api"])
        self.host = host
        self.port = port

    def start(self):
        super(NovaApiProcess, self).start()
        wait_to_launch(self.host, self.port)


class NovaComputeProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaComputeProcess, self)\
                .__init__(directory, ["sg", "libvirtd",
                                      "bin/nova-compute"])

    def start(self):
        super(NovaComputeProcess, self).start()
        time.sleep(5)

    def stop(self):
        kill_children_process(self._process.pid)
        super(NovaComputeProcess, self).stop()


class NovaNetworkProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaNetworkProcess, self)\
                .__init__(directory, ["bin/nova-network"])


class NovaSchedulerProcess(NovaProcess):
    def __init__(self, directory):
        super(NovaSchedulerProcess, self)\
                .__init__(directory, ["bin/nova-scheduler"])


class QuantumProcess(Process):
    def __init__(self, directory, config):
        super(QuantumProcess, self)\
                .__init__(directory, ["bin/quantum", config])


class QuantumPluginOvsAgentProcess(Process):
    def __init__(self, directory, config):
        super(QuantumPluginOvsAgentProcess, self)\
                .__init__(directory, ["sudo", "python",
                                      "quantum/plugins/"
                                          "openvswitch/agent/"
                                          "ovs_quantum_agent.py",
                                      config,
                                      "-v"])

    def stop(self):
        kill_children_process(self._process.pid, force=True)
        os.system('/usr/bin/sudo /bin/kill %d' % self._process.pid)
        self._process = None


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

    @attr(type='medium')
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
        resp, flavor = self.client.get_flavor_details(3)
        self.assertEquals('404', resp['status'])
