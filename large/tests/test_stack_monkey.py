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
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, 'ps -ef|grep nova-api|grep -v grep',
                      shell=True)

    def test_start_nova_api(self):

        monkeyutil.start_nova_api()
        subprocess.check_call('ps -ef|grep nova-api|grep -v grep',
                      shell=True)

    def test_stop_glance_api(self):

        monkeyutil.stop_glance_api()
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, 'ps -ef|grep glance-api|grep -v grep',
                      shell=True)

    def test_start_glance_api(self):

        monkeyutil.start_glance_api()
        subprocess.check_call('ps -ef|grep glance-api|grep -v grep',
                      shell=True)

    def test_stop_mysql(self):

        monkeyutil.stop_mysql()
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, 'ps -ef|grep mysql|grep -v grep',
                      shell=True)

    def test_start_mysql(self):

        monkeyutil.start_mysql()
        subprocess.check_call('ps -ef|grep mysql|grep -v grep',
                      shell=True)


    def test_stop_nova_compute(self):

        monkeyutil.stop_nova_compute()
        self.assertRaises(subprocess.CalledProcessError,
            subprocess.check_call, 'ps -ef|grep nova-compute|grep -v grep',
                      shell=True)

    def test_start_nova_compute(self):

        monkeyutil.start_nova_compute()
        subprocess.check_call('ps -ef|grep nova-compute|grep -v grep',
                      shell=True)
