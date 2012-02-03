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
from large.tests import stack_monkey_util as monkeyutil



"""
To test this. Setup environment with the devstack of github.com/ntt-pf-lab/.
"""


class StackMonkeyTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_stop_nova_api(self):

        monkeyutil.stop_nova_api()
        host = monkeyutil.havoc.config.nodes.api.ip
        username = monkeyutil.havoc.config.nodes.api.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-api|grep -v grep'" % (username, host)

        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_nova_api(self):

        monkeyutil.start_nova_api()
        host = monkeyutil.havoc.config.nodes.api.ip
        username = monkeyutil.havoc.config.nodes.api.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-api|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)


    def test_stop_nova_scheduler(self):

        monkeyutil.stop_nova_scheduler()
        host = monkeyutil.havoc.config.nodes.scheduler.ip
        username = monkeyutil.havoc.config.nodes.scheduler.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-scheduler|grep -v grep'" % (username, host)

        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_nova_scheduler(self):

        monkeyutil.start_nova_scheduler()
        host = monkeyutil.havoc.config.nodes.scheduler.ip
        username = monkeyutil.havoc.config.nodes.scheduler.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-scheduler|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)


    def test_stop_nova_network(self):

        monkeyutil.stop_nova_network()
        host = monkeyutil.havoc.config.nodes.network.ip
        username = monkeyutil.havoc.config.nodes.network.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-network|grep -v grep'" % (username, host)

        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_nova_network(self):

        monkeyutil.start_nova_network()
        host = monkeyutil.havoc.config.nodes.network.ip
        username = monkeyutil.havoc.config.nodes.network.user
        pscmd = "ssh %s@%s 'ps -ef|grep nova-network|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)


    def test_stop_quantum(self):

        monkeyutil.stop_quantum()
        host = monkeyutil.havoc.config.nodes.network.ip
        username = monkeyutil.havoc.config.nodes.network.user
        pscmd = "ssh %s@%s 'ps -ef|grep quantum|grep -v grep'" % (username, host)

        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_quantum(self):

        monkeyutil.start_quantum()
        host = monkeyutil.havoc.config.nodes.network.ip
        username = monkeyutil.havoc.config.nodes.network.user
        pscmd = "ssh %s@%s 'ps -ef|grep quantum|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)





    def test_stop_glance_api(self):

        monkeyutil.stop_glance_api()
        host = monkeyutil.havoc.config.nodes.glance.ip
        username = monkeyutil.havoc.config.nodes.glance.user
        pscmd = "ssh %s@%s 'ps -ef|grep glance-api|grep -v grep'" % (username, host)

        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_glance_api(self):

        monkeyutil.start_glance_api()
        host = monkeyutil.havoc.config.nodes.glance.ip
        username = monkeyutil.havoc.config.nodes.glance.user

        pscmd = "ssh %s@%s 'ps -ef|grep glance-api|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)

    def test_stop_mysql(self):

        monkeyutil.stop_mysql()
        host = monkeyutil.havoc.config.nodes.mysql.ip
        username = monkeyutil.havoc.config.nodes.mysql.user

        pscmd = "ssh %s@%s 'ps -ef|grep mysql|grep -v grep'" % (username, host)
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_mysql(self):

        monkeyutil.start_mysql()
        host = monkeyutil.havoc.config.nodes.mysql.ip
        username = monkeyutil.havoc.config.nodes.mysql.user

        pscmd = "ssh %s@%s 'ps -ef|grep mysql|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)


    def test_stop_rabbitmq(self):

        monkeyutil.stop_rabbitmq()
        host = monkeyutil.havoc.config.nodes.rabbitmq.ip
        username = monkeyutil.havoc.config.nodes.rabbitmq.user

        pscmd = "ssh %s@%s 'ps -ef|grep rabbitmq|grep -v grep'" % (username, host)
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)


    def test_start_rabbitmq(self):

        monkeyutil.start_rabbitmq()
        host = monkeyutil.havoc.config.nodes.rabbitmq.ip
        username = monkeyutil.havoc.config.nodes.rabbitmq.user

        pscmd = "ssh %s@%s 'ps -ef|grep rabbitmq|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)


    def test_stop_nova_compute(self):

        monkeyutil.stop_nova_compute()
        host = monkeyutil.havoc.config.nodes.compute.ip
        username = monkeyutil.havoc.config.nodes.compute.user

        pscmd = "ssh %s@%s 'ps -ef|grep nova-compute|grep -v grep'" % (username, host)
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, pscmd,
                      shell=True)

    def test_start_nova_compute(self):

        monkeyutil.start_nova_compute()
        host = monkeyutil.havoc.config.nodes.compute.ip
        username = monkeyutil.havoc.config.nodes.compute.user

        pscmd = "ssh %s@%s 'ps -ef|grep nova-compute|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)

    def test_start_nova_compute_with_patch(self):

        fake_path = 'create-error'
        patch = []
        patch.append(('nova.db.api',
                      'fake_db.db_stop_patch'))
        monkeyutil.start_nova_compute_with_patch(fake_path, patch)
        host = monkeyutil.havoc.config.nodes.compute.ip
        username = monkeyutil.havoc.config.nodes.compute.user

        pscmd = "ssh %s@%s 'ps -ef|grep nova-compute|grep -v grep'" % (username, host)
        subprocess.check_call(pscmd,
                      shell=True)