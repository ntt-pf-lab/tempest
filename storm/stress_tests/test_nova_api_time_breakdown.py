from nose.plugins.attrib import attr
from datetime import datetime, timedelta
import os
import re
import shutil
from stackmonkey import manager
from stackmonkey import config
from storm import openstack
from storm import exceptions
import storm.config
from storm.common.log_parser import CustomLogParser
from storm.common.utils.data_utils import rand_name
from storm.common import sftp
from storm.stress_tests.utils import RequestThread
import sys
import time
import unittest2 as unittest

#configuration files details for test
CONFIG_PATH = os.path.dirname(__file__)
DEFAULT_NOVA_CONF = "nova.conf"
API_PASTE_WITH_DEBUGLOG = "nova-api-paste-with-debuglog.ini"
API_PASTE = "nova-api-paste-without-debuglog.ini"
#service start up wait period (in seconds)
WAIT_TIME = 3
LIST_SERVER_TIMEOUT = 2
CREATE_SERVER_TIMEOUT = 2
#temporary file to which request specific logs are written.
TIME_BREAKDOWN_LOGFILE = "nova_api_time_breakdown_result.log"
#file containing server logs (to read from )
SERVER_LOGFILE = "/var/log/user.log"
DATETIME_REGEX = '(?P<date_time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


class NovaPerfTimeBreakdownTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = storm.config.StormConfig()
        cls.havoc_config = config.HavocConfig()
        cls.image_ref = cls.config.env.image_ref
        cls.flavor_ref = cls.config.env.flavor_ref
        cls.ssh_timeout = cls.config.nova.ssh_timeout
        #fetch the debuglogger_enabled status.
        cls.debuglogger_enabled = bool(cls.config.env.get(
            'debuglogger_enabled', True))

        #create Nova conf file with debuglogger setting as specified in conf.
        nova_conf = cls._create_nova_conf(cls.debuglogger_enabled)

        #start Nova services using the above Nova conf file.
        cls._start_services(nova_conf)

        #fetch the number of times an API should be hit.
        try:
            cls.perf_api_hit_count = int(cls.config.env.get(
                'perf_api_hit_count', 10))
        except ValueError:
            print "Invalid 'perf_api_hit_count=%s' specified!" % \
                  cls.config.env.get('perf_api_hit_count', None)
            sys.exit(1)
        #fetch the thread count.
        try:
            cls.perf_thread_count = int(cls.config.env.get(
                'perf_thread_count', 1))
        except ValueError:
            print "Invalid 'perf_thread_count=%s' specified!" % \
                  cls.config.env.get('perf_thread_count', None)
            sys.exit(1)
        #remove the last run results.
        if os.path.exists(TIME_BREAKDOWN_LOGFILE):
            os.remove(TIME_BREAKDOWN_LOGFILE)
        #create 2 instances so that list servers API has some results
        cls._instance_ids = []
        cls._start_instances()

    @classmethod
    def tearDownClass(cls):
        #delete the instance(s) started for List Servers API.
        for instance_id in cls._instance_ids:
            try:
                resp, body = cls.client.delete_server(instance_id)
            except exceptions.BadRequest:
                print "Failed to stop instance id %s" % instance_id
            else:
                if resp.status != 204:
                    print "Failed to stop instance id %s" % instance_id

    @classmethod
    def _start_services(cls, nova_conf):
        run_tests = True

        #fetch the config parameters and verify deploy mode.
        if cls.havoc_config.env.deploy_mode == 'pkg-multi':
            nodes = cls.havoc_config.nodes
            api_mgr = manager.ControllerHavoc(nodes.api.ip, nodes.api.user,
                                                nodes.api.password)
            new_api_mgr = manager.ControllerHavoc(nodes.api.ip,
                                                  nodes.api.user,
                                                  nodes.api.password,
                                                  config_file=nova_conf)
            if isinstance(nodes.compute, list):
                compute_mgr = []
                new_compute_mgr = []
                for compute in nodes.compute:
                    cmp_mgr = manager.ComputeHavoc(compute.ip,
                                                    compute.user,
                                                    compute.password)
                    compute_mgr.append(cmp_mgr)
                    new_cmp_mgr = manager.ComputeHavoc(compute.ip,
                                                    compute.user,
                                                    compute.password,
                                                    config=nova_conf)
                    new_compute_mgr.append(new_cmp_mgr)
            else:
                compute_mgr = manager.ComputeHavoc(nodes.compute.ip,
                                                    nodes.compute.user,
                                                    nodes.compute.password)
                new_compute_mgr = manager.ComputeHavoc(compute.ip,
                                                    compute.user,
                                                    compute.password,
                                                    config=nova_conf)

            scheduler_mgr = manager.ControllerHavoc(nodes.scheduler.ip,
                                                nodes.scheduler.user,
                                                nodes.scheduler.password)
            if nodes.network:
                network_mgr = manager.NetworkHavoc(nodes.network.ip,
                                                nodes.network.user,
                                                nodes.network.password)
                new_network_mgr = manager.NetworkHavoc(nodes.network.ip,
                                                nodes.network.user,
                                                nodes.network.password,
                                                config=nova_conf)
        else:
            mgr = manager.ControllerHavoc()
            api_mgr = scheduler_mgr = mgr
            new_api_mgr = manager.ControllerHavoc(config_file=nova_conf)

            compute_mgr = manager.ComputeHavoc()
            new_compute_mgr = manager.ComputeHavoc(config_file=nova_conf)
            network_mgr = manager.NetworkHavoc()
            network_mgr = manager.NetworkHavoc(config_file=nova_conf)

        #start all the Nova services.
        scheduler_mgr.start_nova_scheduler()
        #start Nova API using the new Nova conf file
        api_mgr.stop_nova_api()
        new_api_mgr.start_nova_api()

        #start all the Compute services.
        if isinstance(compute_mgr, list):
            for compute_node in compute_mgr:
                compute_node.stop_nova_compute()
                new_compute_mgr.start_nova_compute()
        else:
            compute_mgr.stop_nova_compute()
            new_compute_mgr.start_nova_compute()

        #determine whether to start Quantum or Network services from nova.conf
        #in the perf_tests directory.
        conf_fp = open(os.path.join(CONFIG_PATH, DEFAULT_NOVA_CONF))
        for line in conf_fp.readlines():
            if line.startswith("--network_manager"):
                if line.find("QuantumManager") != -1:
                    quantum_mgr.start_quantum()
                else:
                    network_mgr.stop_nova_network()
                    new_network_mgr.start_nova_network()
                break
        conf_fp.close()

        #determine if Keystone service should be started.
        if cls.config.env.authentication.find("keystone") != -1:
            keystone_mgr.start_keystone()

        if not run_tests:
            print "Failed to start the services required for executing tests."
            sys.exit()
        #wait for the services to start completely
        time.sleep(WAIT_TIME)

    @classmethod
    def _start_instances(cls):
        """Start 2 instances so that List Servers has some results."""
        for index in range(2):
            name = rand_name('server')
            try:
                resp, body = cls.client.create_server(name,
                                                      cls.image_ref,
                                                      cls.flavor_ref)
            except exceptions.BadRequest:
                print "Failed to start instances"
                sys.exit()
            else:
                if resp.status != 202:
                    print "Failed to start instances"
                    sys.exit()
                cls._instance_ids.append(body['id'])

    @classmethod
    def _copy_file_to_api_server(cls, localpath, remotepath):
        """Copy the specified file to the Nova API server in specified path."""
        if cls.havoc_config.env.deploy_mode in ('pkg-multi',
                                                'devstack-remote'):
            #do remote copy.
            api = cls.havoc_config.nodes.api
            sftp_session = sftp.Client(api.ip, api.user, api.password)
            return sftp_session.put(localpath, remotepath)
        else:
            #do a local copy.
            try:
                shutil.copy(localpath, remotepath)
                return True
            except IOError:
                return False

    @classmethod
    def _create_nova_conf(cls, debuglog_enabled):
        """Update log level and api-paste config path in nova.conf"""
        #copy the nova.conf file to the API server.
        src = os.path.join(CONFIG_PATH, DEFAULT_NOVA_CONF)
        config_name = "/tmp/nova_perf_test.conf"
        try:
            shutil.copy(src, config_name)
        except IOError:
            print "Failed to copy copy %(src)s to %(config_name)s" % locals()
            sys.exit(1)

        append_conf = "--verbose"
        if debuglog_enabled:
            paste_path = os.path.join(CONFIG_PATH, API_PASTE_WITH_DEBUGLOG)
            api_paste_config = os.path.join("/tmp", API_PASTE_WITH_DEBUGLOG)
        else:
            paste_path = os.path.join(CONFIG_PATH, API_PASTE)
            api_paste_config = os.path.join("/tmp", API_PASTE)
        #copy the paste.ini file to the API server.
        status = cls._copy_file_to_api_server(paste_path, api_paste_config)
        if not status:
            print "Failure copying configuration file %s to API server." % src
            sys.exit(1)

        append_conf += "\n--api_paste_config=%s" % api_paste_config
        fp = open(config_name, "a")
        fp.write(append_conf)
        fp.close()

        #copy updated (log level and api-paste config) nova.conf to API server.
        if cls.havoc_config.env.deploy_mode in ('pkg-multi',
                                                'devstack-remote'):
            dest_config_name = "/etc/nova/nova.conf"
            status = cls._copy_file_to_api_server(config_name,
                                                    dest_config_name)
            if not status:
                print "Failure copying configuration file %s "\
                      "to API server." % src
                sys.exit(1)
        else:
            dest_config_name = config_name
        return dest_config_name

    def call_list_servers_api(self):
        """Call the List servers API and return response"""
        response = {'status': True, 'response_time': [], 'request_id': []}
        expected_status = (200, 203)
        os = openstack.Manager()
        client = os.servers_client
        for index in range(self.perf_api_hit_count):
            try:
                resp, body = client.list_servers()
            except:
                response['status'] = False
                break
            else:
                if resp.status not in expected_status:
                    response['status'] = False
                    break
            response['response_time'].append(client.client.response_time)
            response['request_id'].append(resp['request_id'])
        return response

    def _log_testcase_results(self, result_str):
        fp = open(TIME_BREAKDOWN_LOGFILE, "a")
        fp.write(result_str)
        fp.close()

    def _get_time_breakdown(self, request_logs, log_list):
        """Fetch the time taken for each log msg from log_list """
        mObj = re.search(DATETIME_REGEX, request_logs[0])
        self.assertNotEqual(mObj, None, "Server date format unknown")
        start_time = datetime.strptime(mObj.group('date_time'), DATE_FORMAT)

        mObj = re.search(DATETIME_REGEX, request_logs[-1])
        self.assertNotEqual(mObj, None, "Server date format unknown")
        end_time = datetime.strptime(mObj.group('date_time'), DATE_FORMAT)

        task_time = []
        last_time = start_time
        start_index = 0
        for log_msg in log_list:
            found = False
            for index in range(start_index, len(request_logs)):
                mObj = re.search(log_msg % DATETIME_REGEX, request_logs[index])
                if mObj:
                    #log found.
                    current_time = datetime.strptime(mObj.group('date_time'),
                                        DATE_FORMAT)
                    time_taken = current_time - last_time
                    last_time = current_time
                    task_time.append(time_taken)
                    found = True
                    start_index = index
                    break
            self.assertTrue(found, "Expected log message %s not found" %
                                   log_msg)
        task_time.append(end_time - last_time)
        return (task_time, start_time, end_time)

    def _convert_timedelta_to_milliseconds(self, td):
        """convert timedelta to milliseconds"""
        ms = td.days * 86400 * 1E3 + td.seconds * 1E3 + td.microseconds / 1E3
        return ms

    def _verify_list_servers_api_perf(self):
        """Verified list servers API and fetch the perf breakdown."""
        request_serve_time = {}

        #hit the API
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_list_servers_api))
            request_threads[index].start()  # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(LIST_SERVER_TIMEOUT)
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("List server API %d calls did not complete in %.2f "\
                            "seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            resp = a_thread.get_response()

            if not resp['status']:
                self.fail("List servers API call failed")
            temp_results = zip(resp['request_id'], resp['response_time'])
            request_serve_time.update(temp_results)

        #fetch the API request logs.
        log_parser = CustomLogParser(SERVER_LOGFILE)
        log_list = ['%s nova-api INFO [\s\S]+ GET [\S]+\/servers$',
                    '%s nova-api DEBUG [\s\S]+ get_all',
                    '%s nova-api INFO [\s\S]+ returned with HTTP']
        test_time = {'routing': 0, 'db_look_up': 0, 'total_time': 0,
                     'max_routing_time': 0, 'max_db_lookup_time': 0,
                     'max_request_time': 0, 'min_routing_time': 9999,
                     'min_db_lookup_time': 9999, 'min_request_time': 9999}
        log_str = "\nList Servers API Test Results\n"\
            "Request Routing Time\tDB look up Time\t\tTotal time\n"

        for request_id, response_time in request_serve_time.iteritems():
            filtered_logs = log_parser.fetch_request_logs(request_id)
            if not filtered_logs:
                self.fail("Failed to fetch logs for request %(request_id)s" %
                          locals())
            (opt_time, start_time, end_time) = self._get_time_breakdown(
                                                    filtered_logs, log_list)
            routing_time = self._convert_timedelta_to_milliseconds(
                            opt_time[0])
            db_lookup_time = self._convert_timedelta_to_milliseconds(
                                        opt_time[2])
            test_time['routing'] += routing_time
            if test_time['max_routing_time'] < routing_time:
                test_time['max_routing_time'] = routing_time
            if test_time['min_routing_time'] > routing_time:
                test_time['min_routing_time'] = routing_time
            test_time['db_look_up'] += db_lookup_time
            if test_time['max_db_lookup_time'] < db_lookup_time:
                test_time['max_db_lookup_time'] = db_lookup_time
            if test_time['min_db_lookup_time'] > db_lookup_time:
                test_time['min_db_lookup_time'] = db_lookup_time
            secs, msecs = response_time.split('.')
            total_time = self._convert_timedelta_to_milliseconds(timedelta(
                                seconds=int(secs), microseconds=int(msecs)))
            test_time['total_time'] += total_time
            if test_time['max_request_time'] < total_time:
                test_time['max_request_time'] = total_time
            if test_time['min_request_time'] < total_time:
                test_time['min_request_time'] = total_time

            log_str += "%(routing_time)d\t\t\t%(db_lookup_time)d\t\t\t"\
                        "%(total_time)d\n" % locals()
        #log individual request results
        self._log_testcase_results(log_str)
        return test_time

    def test_list_servers_performance_breakdown(self):
        """Call List Servers API and record time for each activity."""
        test_time = self._verify_list_servers_api_perf()

        #write the summary results to output file.
        total_requests = self.perf_thread_count * self.perf_api_hit_count
        avg_routing_time = test_time['routing'] / total_requests
        avg_dblookup_time = test_time['db_look_up'] / total_requests
        avg_response_time = test_time['total_time'] / total_requests
        result_str = "*" * 50 + "\n"\
            "Total API requests: %(total_requests)d\n"\
            "\nAverage Request routing time:\t%(avg_routing_time)d "\
            "milliseconds\n"\
            "Average DB lookup time:\t\t%(avg_dblookup_time)d milliseconds\n"\
            "Average request serve time:\t%(avg_response_time)d "\
            "milliseconds\n\n" % locals()

        result_str += "Minimum request routing time:\t%(min_routing_time)d "\
            "milliseconds\n"\
            "Minimum DB lookup time:\t\t%(min_db_lookup_time)d milliseconds\n"\
            "Minimum request serve time:\t%(min_request_time)d "\
            "milliseconds\n\n"\
            "Maximum request routing time:\t%(max_routing_time)d "\
            "milliseconds\n"\
            "Maximum DB lookup time:\t\t%(max_db_lookup_time)d milliseconds\n"\
            "Maximum request serve time:\t%(max_request_time)d "\
            "milliseconds\n" % test_time
        self._log_testcase_results(result_str)

    def call_create_servers_api(self):
        """Call the Create servers API and return response"""
        kwargs = {'image_ref': self.image_ref,
                  'flavor_ref': self.flavor_ref}
        response = {'status': True, 'response_time': [], 'server_ids': [],
                    'request_id': []}
        expected_status = (202, )
        os = openstack.Manager()
        client = os.servers_client
        for index in range(self.perf_api_hit_count):
            kwargs['name'] = rand_name('server')
            try:
                resp, body = client.create_server(**kwargs)
            except:
                response['status'] = False
                break
            else:
                if resp.status not in expected_status:
                    response['status'] = False
                    break
            response['response_time'].append(client.client.response_time)
            response['server_ids'].append(body['id'])
            response['request_id'].append(resp['request_id'])
        return response

    def _verify_create_servers_api_perf(self):
        """Verified create servers API and fetch the perf breakdown."""
        request_serve_time = {}

        #hit the API
        os = openstack.Manager()
        client = os.servers_client
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_create_servers_api))
            request_threads[index].start()  # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(CREATE_SERVER_TIMEOUT)
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("Create server API %d calls did not complete in "\
                            "%.2f seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            resp = a_thread.get_response()

            if not resp['status']:
                self.fail("Create servers API call failed")
            temp_results = zip(resp['request_id'], resp['response_time'])
            request_serve_time.update(temp_results)
            # wait for all the instances to become ACTIVE.
            for instance_id in resp['server_ids']:
                client.wait_for_server_status(instance_id, 'ACTIVE')

        #fetch the API request logs.
        log_parser = CustomLogParser(SERVER_LOGFILE)
        log_list = [
            '%s nova-api INFO [\s\S]+ POST [\S]+\/servers$',
            '%s nova-api DEBUG [\s\S]+ Using Kernel=',
            '%s nova-api DEBUG [\s\S]+ Going to run 1 instances',
            '%s nova-api DEBUG [\s\S]+ block_device_mapping',
            '%s nova-api DEBUG [\s\S]+ _ask_scheduler_to_create_instance',
            '%s nova-compute AUDIT [\s\S]+ instance \d+: starting',
            '%s nova-compute DEBUG [\s\S]+ Making asynchronous call on '\
                'network',
            '%s nova-network DEBUG [\s\S]+ floating IP allocation for '\
                'instance',
            '%s nova-compute DEBUG [\s\S]+ instance network_info',
            '%s nova-compute DEBUG [\s\S]+ starting toXML method',
            '%s nova-compute DEBUG [\s\S]+ finished toXML method',
            '%s nova-compute INFO [\s\S]+ called setup_basic_filtering in '\
                'nwfilter',
            '%s nova-compute INFO [\s\S]+ Creating image',
            '%s nova-compute DEBUG [\s\S]+ Creating kernel image',
            '%s nova-compute DEBUG [\s\S]+ Fetching image',
            '%s nova-compute DEBUG [\s\S]+ Fetched image',
            '%s nova-compute DEBUG [\s\S]+ Created kernel image',
            # TODO: provide optional log message support and then uncomment.
            #'%s nova-compute DEBUG [\s\S]+ Creating ramdisk image',
            #'%s nova-compute DEBUG [\s\S]+ Fetching image',
            #'%s nova-compute DEBUG [\s\S]+ Fetched image',
            #'%s nova-compute DEBUG [\s\S]+ Created ramdisk image',
            '%s nova-compute DEBUG [\s\S]+ Creating disk image',
            '%s nova-compute DEBUG [\s\S]+ Fetching image',
            '%s nova-compute DEBUG [\s\S]+ Fetched image',
            '%s nova-compute DEBUG [\s\S]+ Created disk image',
            '%s nova-compute DEBUG [\s\S]+ instance \S+: is running',
            '%s nova-compute INFO [\s\S]+ Instance \S+ spawned successfully']

        #test results dict.
        test_time = {'routing': 0, 'check_params': 0, 'block_device': 0,
                     'scheduling': 0, 'api_response_time': 0,
                     'starting_instance': 0, 'networking': 0,
                     'xml_generation': 0, 'firewall': 0,
                     'image_fetch_time': 0, 'image_create_time': 0,
                     'create_kernel_img': 0, 'create_ramdisk_img': 0,
                     'create_disk_img': 0,
                     'start_instance': 0, 'boot_instance': 0,
                     'api_response_time': 0, 'total_time': 0,
                     'nova_api': 0, 'nova_scheduler': 0, 'nova_compute': 0,
                     'nova_network': 0,
                     'max_network_time': 0, 'max_boot_time': 0,
                     'max_start_instance': 0, 'max_request_time': 0,
                     'max_img_fetch_time': 0, 'max_img_create_time': 0,
                     'min_network_time': 9999, 'min_boot_time': 9999,
                     'min_start_instance': 9999, 'min_request_time': 9999,
                     'min_img_fetch_time': 9999, 'min_img_create_time': 9999,
                     }
        #fields logged for each API request.
        log_str = "\nCreate Servers API Test Results\n"\
            "Routing\tParam Check\tBlock Device Mapping\tScheduling\t"\
            "Networking\tCompute\t\tKernel Image Fetch\tKernel Image Create"\
            "\tDisk Image Fetch\tDisk Image Create\t"\
            "Image Creation\tInstance Boot\tAPI Response\tTotal time\n"

        for request_id, response_time in request_serve_time.iteritems():
            filtered_logs = log_parser.fetch_request_logs(request_id)
            if not filtered_logs:
                self.fail("Failed to fetch logs for request %(request_id)s" %
                          locals())

            (opt_time, start_time, end_time) = self._get_time_breakdown(
                                                    filtered_logs, log_list)

            routing_time = self._convert_timedelta_to_milliseconds(
                            opt_time[0])
            check_parameters_time = self._convert_timedelta_to_milliseconds(
                            opt_time[2])
            block_device_mapping = self._convert_timedelta_to_milliseconds(
                                        opt_time[4])

            secs, msecs = response_time.split('.')
            api_response_time = self._convert_timedelta_to_milliseconds(
                timedelta(seconds=int(secs), microseconds=int(msecs)))

            schedule_time = self._convert_timedelta_to_milliseconds(
                                        opt_time[5])
            start_instance_time = self._convert_timedelta_to_milliseconds(
                                        opt_time[6])
            network_floating_ip_allocation_time = \
                self._convert_timedelta_to_milliseconds(opt_time[8])
            compute_xml_generation_time = \
                self._convert_timedelta_to_milliseconds(opt_time[10])
            compute_instance_firewall_setup = \
                self._convert_timedelta_to_milliseconds(opt_time[12])

            compute_kernel_img_fetch = \
                self._convert_timedelta_to_milliseconds(opt_time[15])
            compute_kernel_img_create = compute_kernel_img_fetch +\
                self._convert_timedelta_to_milliseconds(opt_time[16])
            #TODO: uncomment once optional log message support is added.
            #compute_ramdisk_img_fetch = \
            #    self._convert_timedelta_to_milliseconds(opt_time[19])
            #compute_ramdisk_img_create = compute_ramdisk_img_fetch +\
            #    self._convert_timedelta_to_milliseconds(opt_time[20])
            compute_disk_img_fetch = \
                self._convert_timedelta_to_milliseconds(opt_time[19])
            compute_disk_img_create = compute_disk_img_fetch +\
                self._convert_timedelta_to_milliseconds(opt_time[20])

            compute_start_instance = \
                self._convert_timedelta_to_milliseconds(opt_time[21])
            compute_boot_instance = \
                self._convert_timedelta_to_milliseconds(opt_time[22])

            # total time right from API call was hit to instance status is
            # ACTIVE.
            active_instance_creation_time = \
                self._convert_timedelta_to_milliseconds(end_time - start_time)

            img_fetch_time = compute_kernel_img_fetch + compute_disk_img_fetch
            img_create_time = compute_kernel_img_create +\
                              compute_disk_img_create

            test_time['routing'] += routing_time
            test_time['check_params'] += check_parameters_time
            test_time['block_device'] += block_device_mapping
            test_time['scheduling'] += schedule_time
            test_time['image_fetch_time'] += img_fetch_time
            test_time['create_kernel_img'] += compute_kernel_img_create
            #TODO: uncomment once optional log message support is added.
            #test_time['create_ramdisk_img'] +=
            test_time['create_disk_img'] += compute_disk_img_create
            test_time['image_create_time'] += img_create_time
            test_time['starting_instance'] += start_instance_time
            test_time['networking'] += network_floating_ip_allocation_time
            test_time['xml_generation'] += compute_xml_generation_time
            test_time['firewall'] += compute_instance_firewall_setup
            test_time['start_instance'] += \
                compute_start_instance
            test_time['boot_instance'] += compute_boot_instance
            test_time['api_response_time'] += api_response_time
            test_time['total_time'] += active_instance_creation_time

            test_time['nova_api'] += routing_time + check_parameters_time +\
                                     block_device_mapping
            test_time['nova_scheduler'] += schedule_time
            compute_time = compute_kernel_img_fetch +\
                           compute_disk_img_fetch +\
                           start_instance_time +\
                           compute_xml_generation_time +\
                           compute_instance_firewall_setup +\
                           compute_start_instance
            test_time['nova_compute'] += compute_time
            test_time['nova_network'] += network_floating_ip_allocation_time

            if test_time['max_boot_time'] < compute_boot_instance:
                test_time['max_boot_time'] = compute_boot_instance
            if test_time['min_boot_time'] > compute_boot_instance:
                test_time['min_boot_time'] = compute_boot_instance
            if test_time['max_img_fetch_time'] < img_fetch_time:
                test_time['max_img_fetch_time'] = img_fetch_time
            if test_time['min_img_fetch_time'] > img_fetch_time:
                test_time['min_img_fetch_time'] = img_fetch_time
            if test_time['max_img_create_time'] < img_create_time:
                test_time['max_img_create_time'] = img_create_time
            if test_time['min_img_create_time'] > img_create_time:
                test_time['min_img_create_time'] = img_create_time

            if test_time['max_network_time'] < \
                network_floating_ip_allocation_time:
                test_time['max_network_time'] = \
                    network_floating_ip_allocation_time
            if test_time['min_network_time'] > \
                network_floating_ip_allocation_time:
                test_time['min_network_time'] = \
                    network_floating_ip_allocation_time
            if test_time['max_start_instance'] < \
                compute_start_instance:
                test_time['max_start_instance'] = \
                    compute_start_instance
            if test_time['min_start_instance'] > \
                compute_start_instance:
                test_time['min_start_instance'] = \
                    compute_start_instance
            if test_time['max_request_time'] < api_response_time:
                test_time['max_request_time'] = api_response_time
            if test_time['min_request_time'] > api_response_time:
                test_time['min_request_time'] = api_response_time

            log_str += "%(routing_time)d\t%(check_parameters_time)d\t\t"\
                "%(block_device_mapping)d\t\t\t%(schedule_time)d\t\t"\
                "%(network_floating_ip_allocation_time)d\t\t%(compute_time)d"\
                "\t\t%(compute_kernel_img_fetch)d\t"\
                "%(compute_kernel_img_create)d\t%(compute_disk_img_fetch)d"\
                "\t%(compute_disk_img_create)d"\
                "\t\t%(compute_boot_instance)d\t\t%(api_response_time)d\t\t"\
                "%(active_instance_creation_time)d\n" % locals()
        #log individual request results
        self._log_testcase_results(log_str + "\n")
        return test_time

    def test_create_servers_performance_breakdown(self):
        """Call Create Servers API and record time for each activity."""
        test_time = self._verify_create_servers_api_perf()

        #write the summary results to output file.
        total_requests = self.perf_thread_count * self.perf_api_hit_count
        avg_nova_api = test_time['nova_api'] / total_requests
        avg_nova_nova_network = test_time['nova_network'] / total_requests
        avg_nova_compute = test_time['nova_compute'] / total_requests
        avg_nova_scheduler = test_time['nova_scheduler'] / total_requests

        result_str = "*" * 50 + "\n"\
            "Total API requests: %(total_requests)d\n"\
            "Average Nova API time: %(avg_nova_api)d milliseconds\n"\
            "Average Nova Scheduler time: %(avg_nova_scheduler)d "\
            "milliseconds\n"\
            "Average Nova Compute time: %(avg_nova_compute)d milliseconds\n"\
            "Average Nova Network time: %(avg_nova_nova_network)d "\
            "milliseconds\n\n" % locals()

        result_str += "Minimum Request Serve time: %(min_request_time)d "\
            "milliseconds\n"\
            "Minimum image fetching time: %(min_img_fetch_time)d "\
            "milliseconds\n"\
            "Minimum image creation time: %(min_img_create_time)d "\
            "milliseconds\n"\
            "Minimum start time: %(min_start_instance)d milliseconds\n"\
            "Minimum instance boot time: %(min_boot_time)d milliseconds\n"\
            "Minimum networking time: %(min_network_time)d milliseconds\n\n"\
            "Maximum Request Serve time: %(max_request_time)d milliseconds\n"\
            "Maximum image fetching time: %(max_img_fetch_time)d "\
            "milliseconds\n"\
            "Maximum image creation time: %(max_img_create_time)d "\
            "milliseconds\n"\
            "Maximum start time: %(max_start_instance)d milliseconds\n"\
            "Maximum instance boot time: %(max_boot_time)d milliseconds\n"\
            "Maximum networking time: %(max_network_time)d "\
            "milliseconds\n" % test_time

        self._log_testcase_results(result_str)
