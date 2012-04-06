# Copyright 2011 Quanta Research Cambridge, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
"""Test that reboots random instances in a Nova cluster"""


from stress.test_servers import *
from stress.test_server_actions import *
from stress.basher import BasherAction
from stress.driver import *
from tempest import openstack

choice_spec = [
    BasherAction(TestCreateVM(), 50),
    BasherAction(TestRebootVM(), 50,
                 kargs={'type': 'HARD'})
]

nova = openstack.Manager()

bash_openstack(nova,
               choice_spec,
               duration=datetime.timedelta(seconds=180),
               sleep_time=500,  # in milliseconds
               seed=int(time.time()),
               test_name="hard reboots",
               )
