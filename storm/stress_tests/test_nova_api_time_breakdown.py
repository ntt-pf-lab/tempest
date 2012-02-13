from nose.plugins.attrib import attr
from datetime import timedelta
import os
import shutil
from stackmonkey import manager
from stackmonkey import config
from storm import openstack
from storm import exceptions
import storm.config
from storm.common.utils.data_utils import rand_name
from storm.common import sftp
from storm.stress_tests import utils
import sys
import time
import unittest2 as unittest

#configuration files details for test
CONFIG_PATH = os.path.dirname(__file__)
DEFAULT_NOVA_CONF = "nova.conf"
API_PASTE_WITH_DEBUGLOG = "nova-api-paste-with-debuglog.ini"
API_PASTE = "nova-api-paste-without-debuglog.ini"
#temporary file to which request specific logs are written.
TIME_BREAKDOWN_LOGFILE = "nova_api_time_breakdown_result.log"
DATETIME_REGEX = '(?P<date_time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


class NovaPerfTimeBreakdownTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = storm.config.StormConfig()
        cls.havoc_config = config.HavocConfig()

        #fetch the Perf test configuration parameters
        cls._fetch_config_params()

        #create Nova conf file with debuglogger setting as specified in conf.
        nova_conf = cls._create_nova_conf(cls.debuglogger_enabled)

        #start Nova services using the above Nova conf file.
        cls._start_services(nova_conf)

        #remove the last run results.
        if os.path.exists(TIME_BREAKDOWN_LOGFILE):
            os.remove(TIME_BREAKDOWN_LOGFILE)
        #create 2 instances so that list servers API has some results
        cls._instance_ids = []
        #cls._start_instances()

    @classmethod
    def _fetch_param_value(cls, param, type, default_value):
        try:
            value = type(cls.config.env.get(param, default_value))
        except ValueError:
            value = cls.config.env.get(param, None)
            print "Invalid configuration value '%(value)s' specified for "\
                  "%(param)s!" % locals()
            sys.exit(1)
        return value

    @classmethod
    def _fetch_config_params(cls):
        """Fetch the configuration parameters"""
        cls.image_ref = cls._fetch_param_value('image_ref', str, '2')
        cls.flavor_ref = cls._fetch_param_value('flavor_ref', str, '1')
        #fetch the debuglogger_enabled status.
        cls.debuglogger_enabled = cls._fetch_param_value(
            'debuglogger_enabled', bool, True)
        #the number of times an API should be hit.
        cls.perf_api_hit_count = cls._fetch_param_value(
            'perf_api_hit_count', int, 10)
        #number of threads to create.
        cls.perf_thread_count = cls._fetch_param_value(
            'perf_thread_count', int, 1)
        #List server API call timeout
        cls.list_server_timeout = cls._fetch_param_value(
            'list_server_timeout', int, 2)
        #Create server API call timeout
        cls.create_server_timeout = cls._fetch_param_value(
            'create_server_timeout', int, 3)
        #Delete server API call timeout
        cls.delete_server_timeout = cls._fetch_param_value(
            'delete_server_timeout', int, 2)
        #Service start up time
        cls.service_startup_time = cls._fetch_param_value(
            'service_startup_time', int, 3)
        #fetch the Nova service logs from this file.
        cls.server_logfile = cls._fetch_param_value(
            'server_logfile', str, '/var/log/user.log')
        #Nova configuration file path.
        cls.nova_conf_file = cls._fetch_param_value(
            'nova_conf_file', str, '/etc/nova/nova.conf')

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
            new_network_mgr = manager.NetworkHavoc(config_file=nova_conf)

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
                if line.find("QuantumManager") == -1:
                    network_mgr.stop_nova_network()
                    new_network_mgr.start_nova_network()
                break
        conf_fp.close()

        if not run_tests:
            print "Failed to start the services required for executing tests."
            sys.exit()
        #wait for the services to start completely
        time.sleep(cls.service_startup_time)

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
            dest_config_name = cls.nova_conf_file
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

    def _fetch_list_servers_api_response(self):
        """Call list servers API and fetch the response time."""
        request_serve_time = {}

        #hit the API
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(utils.RequestThread(
                self.call_list_servers_api))
            request_threads[index].start()  # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(self.list_server_timeout)
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail(_("List server API %(perf_api_hit_count)d calls "\
                            "did not complete in %(list_server_timeout).2f "\
                            "seconds") % self.__dict__)
            resp = a_thread.get_response()

            if not resp['status']:
                self.fail(_("List servers API call failed: %s") % resp)
            temp_results = zip(resp['request_id'], resp['response_time'])
            request_serve_time.update(temp_results)
        return request_serve_time

    def fetch_list_server_metrics(self, request_serve_time):
        """Fetch the metrics per request and summary metrics"""
        task_logs = [('routing', '%s nova-api INFO [\s\S]+ GET [\S]+\/'
                                 'servers$'),
                    ('fetch_options', '%s nova-api DEBUG [\s\S]+get_all'),
                    ('db_lookup', '%s nova-api INFO [\s\S]+ returned with '
                                  'HTTP')]
        api_results = []
        log_analyzer = utils.LogAnalyzer(self.server_logfile,
                                   DATETIME_REGEX,
                                   DATE_FORMAT)
        for request_id, response_time in request_serve_time.iteritems():
            metrics = log_analyzer.fetch_request_metrics(request_id, task_logs)
            if not metrics:
                self.fail("Failed to fetch logs for request %(request_id)s" %
                          locals())
            secs, msecs = response_time.split('.')
            metrics['task_time']['total_time'] = \
                utils.convert_timedelta_to_milliseconds(
                    timedelta(seconds=int(secs), microseconds=int(msecs)))
            api_results.append(metrics)

        #fetch summary metrics.
        summary_fields = ['routing', 'db_lookup', 'total_time']
        results_summary = log_analyzer.fetch_metrics_summary(api_results,
                                                            summary_fields)
        results_summary['total_requests'] = len(api_results)
        return api_results, results_summary

    def test_list_servers_performance_breakdown(self):
        """Call List Servers API and record time for each activity."""
        request_serve_time = self._fetch_list_servers_api_response()

        api_metrics, results_summary = self.fetch_list_server_metrics(
            request_serve_time)

        log_str = "\nList Servers API Test Results\n"\
            "Request Routing Time\tDB look up Time\t\tTotal time\n"
        for request_metric in api_metrics:
            log_str += "%(routing)d\t\t\t%(db_lookup)d\t\t\t"\
                        "%(total_time)d\n" % request_metric['task_time']

        #fetch the summary metrics.
        log_str += "*" * 50 + "\n"\
            "Total API requests: %(total_requests)d\n"\
            "Average Request routing time:\t%(avg_routing)d milliseconds\n"\
            "Minimum request routing time:\t%(min_routing)d milliseconds\n"\
            "Maximum request routing time:\t%(max_routing)d milliseconds\n\n"\
            "Average DB lookup time:\t\t%(avg_db_lookup)d milliseconds\n"\
            "Minimum DB lookup time:\t\t%(min_db_lookup)d milliseconds\n"\
            "Maximum DB lookup time:\t\t%(max_db_lookup)d milliseconds\n\n"\
            "Average request serve time:\t%(avg_total_time)d "\
            "milliseconds\n"\
            "Minimum request serve time:\t%(min_total_time)d "\
            "milliseconds\n"\
            "Maximum request serve time:\t%(max_total_time)d "\
            "milliseconds\n" % results_summary
        self._log_testcase_results(log_str)

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

    def _fetch_create_servers_api_response(self):
        """Call create servers API and fetch the response time."""
        request_serve_time = {}

        #hit the API
        os = openstack.Manager()
        client = os.servers_client
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(utils.RequestThread(
                self.call_create_servers_api))
            request_threads[index].start()  # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(self.create_server_timeout)
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
        return request_serve_time

    def _fetch_create_server_compute_time(self, task_time):
        """Calculates the time taken by Nova Compute for a Create
        Server API call"""
        return task_time['start_instance'] +\
               task_time['xml_gen'] +\
               task_time['firewall_setup'] +\
               task_time['img_fetch'] + \
               task_time['img_create'] +\
               task_time['boot']

    def _fetch_create_server_nova_api_time(self, task_time):
        """Calculates the time taken by Nova API for a Create Server API
        call"""
        return task_time['routing'] +\
               task_time['check_params'] +\
               task_time['start_bdm'] +\
               task_time['block_device_mapping']

    def _fetch_create_server_img_fetch_time(self, task_time):
        return task_time['krn_img_fetch'] +\
               task_time['rd_img_fetch'] +\
               task_time['disk_img_fetch']

    def _fetch_create_server_img_create_time(self, task_time):
        return task_time['krn_img_create'] +\
               task_time['rd_img_create'] +\
               task_time['disk_img_create']

    def fetch_create_server_metrics(self, request_serve_time):
        """Fetch the metrics per request and summary metrics"""
        task_logs = [
            ('routing', '%s nova-api INFO [\s\S]+ POST [\S]+\/servers$'),
            ('check_params', '%s nova-api DEBUG [\s\S]+ Going to run 1 '
                             'instances'),
            ('start_bdm', '%s nova-api DEBUG [\s\S]+ block_device_mapping'),
            ('block_device_mapping', '%s nova-api DEBUG [\s\S]+ '\
                '_ask_scheduler_to_create_instance'),
            ('starting_instance', '%s nova-compute AUDIT [\s\S]+ instance '\
                                  '\d+: starting'),
            ('start_instance', '%s nova-compute DEBUG [\s\S]+ Making '\
                              'asynchronous call on network'),
            ('network_schedule', '%s nova-network DEBUG [\s\S]+ floating IP '\
                                'allocation for instance'),
            ('ip_allocation', '%s nova-compute DEBUG [\s\S]+ instance '\
                             'network_info'),
            ('start_xml_gen', '%s nova-compute DEBUG [\s\S]+ starting toXML'),
            ('xml_gen', '%s nova-compute DEBUG [\s\S]+ finished toXML'),
            ('start_firewall_setup', '%s nova-compute INFO [\s\S]+ called '\
                                    'setup_basic_filtering in nwfilter'),
            ('firewall_setup', '%s nova-compute INFO [\s\S]+ Creating image'),
            ('start_krn_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                   '\S+kernel image'),
            ('krn_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched '\
                             '\S+kernel image'),
            ('krn_img_create', '%s nova-compute DEBUG [\s\S]+ Created kernel '\
                              'image'),
            ('start_rd_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                  '\S+ramdisk image'),
            ('rd_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched image'),
            ('rd_img_create', '%s nova-compute DEBUG [\s\S]+ Created ramdisk '\
                             'image'),
            ('start_disk_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                    '\S+disk image'),
            ('disk_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched image'),
            ('disk_img_create', '%s nova-compute DEBUG [\s\S]+ Created disk '\
                               'image'),
            ('boot', '%s nova-compute INFO [\s\S]+ Instance \S+ spawned '\
                    'successfully')]

        api_results = []
        log_analyzer = utils.LogAnalyzer(self.server_logfile,
                                   DATETIME_REGEX,
                                   DATE_FORMAT)
        for request_id, response_time in request_serve_time.iteritems():
            metrics = log_analyzer.fetch_request_metrics(request_id, task_logs)
            if not metrics:
                self.fail("Failed to fetch logs for request %(request_id)s" %
                          locals())
            secs, msecs = response_time.split('.')
            metrics['task_time']['api_response_time'] = \
                utils.convert_timedelta_to_milliseconds(
                    timedelta(seconds=int(secs), microseconds=int(msecs)))

            metrics['task_time']['img_fetch'] = \
                self._fetch_create_server_img_fetch_time(metrics['task_time'])
            metrics['task_time']['img_create'] = \
                self._fetch_create_server_img_create_time(metrics['task_time'])
            metrics['task_time']['compute_time'] = \
                self._fetch_create_server_compute_time(metrics['task_time'])
            metrics['task_time']['nova_api_time'] = \
                self._fetch_create_server_nova_api_time(metrics['task_time'])
            total_time = utils.convert_timedelta_to_milliseconds(
                metrics['end_time'] - metrics['start_time'])
            metrics['task_time']['total_time'] = total_time
            api_results.append(metrics)

        #fetch summary metrics.
        summary_fields = metrics['task_time'].keys()
        summary_fields.extend(['compute_time', 'nova_api_time',
                               'api_response_time', 'img_fetch', 'img_create'])
        results_summary = log_analyzer.fetch_metrics_summary(api_results,
                                                            summary_fields)
        results_summary['total_requests'] = len(api_results)
        return api_results, results_summary

    def test_create_servers_performance_breakdown(self):
        """Call Create Servers API and record time for each activity."""
        request_serve_time = self._fetch_create_servers_api_response()

        api_metrics, results_summary = self.fetch_create_server_metrics(
            request_serve_time)

        #fields logged for each API request.
        log_str = "\nCreate Servers API Test Results\n"\
            "Routing\tParam Check\tBlock Device Mapping\tScheduling\t"\
            "Networking\tCompute\t\tKernel Image Fetch\tKernel Image Create"\
            "\tRamdisk Image Fetch\tRamdisk Image Create\t"\
            "\tDisk Image Fetch\tDisk Image Create\t"\
            "Image Creation\tInstance Boot\tAPI Response\tTotal time\n"
        for request_metric in api_metrics:
            log_str += "%(routing)d\t%(check_params)d\t\t"\
                "%(block_device_mapping)d\t\t\t%(network_schedule)d\t\t"\
                "%(ip_allocation)d\t\t%(compute_time)d"\
                "\t\t%(krn_img_fetch)d\t%(krn_img_create)d\t"\
                "\t\t%(rd_img_fetch)d\t%(rd_img_create)d\t"\
                "%(disk_img_fetch)d\t%(disk_img_create)d"\
                "\t\t%(boot)d\t\t%(api_response_time)d\t\t"\
                "%(total_time)d\n" % request_metric['task_time']

        log_str += "*" * 50 + "\n"\
            "Total API requests: %(total_requests)d\n"\
            "Average Active Instance creation time: %(avg_total_time)d "\
            "milliseconds\n"\
            "Average API Response time: %(avg_api_response_time)d "\
            "milliseconds\n"\
            "Average Nova API time: %(avg_nova_api_time)d milliseconds\n"\
            "Average Nova Scheduler time: %(avg_network_schedule)d "\
            "milliseconds\n"\
            "Average Nova Compute time: %(avg_compute_time)d milliseconds\n"\
            "Average Nova Network time: %(avg_ip_allocation)d "\
            "milliseconds\n\n"\
            "Minimum Active Instance creation time: %(min_total_time)d "\
            "milliseconds\n"\
            "Minimum API Response time: %(min_api_response_time)d "\
            "milliseconds\n"\
            "Minimum image fetching time: %(min_img_fetch)d "\
            "milliseconds\n"\
            "Minimum image creation time: %(min_img_create)d "\
            "milliseconds\n"\
            "Minimum instance boot time: %(min_boot)d milliseconds\n"\
            "Minimum networking time: %(min_ip_allocation)d milliseconds\n\n"\
            "Maximum Active Instance creation time: %(max_total_time)d "\
            "milliseconds\n"\
            "Maximum API Response time: %(max_api_response_time)d "\
            "milliseconds\n"\
            "Maximum image fetching time: %(max_img_fetch)d "\
            "milliseconds\n"\
            "Maximum image creation time: %(max_img_create)d "\
            "milliseconds\n"\
            "Maximum instance boot time: %(max_boot)d milliseconds\n"\
            "Maximum networking time: %(max_ip_allocation)d "\
            "milliseconds\n" % results_summary

        self._log_testcase_results(log_str)
