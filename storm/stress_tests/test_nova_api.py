from nose.plugins.attrib import attr
import os
import shutil
from stackmonkey import manager
from stackmonkey import config
from storm import openstack
from storm import exceptions
import storm.config
from storm.common.utils.data_utils import rand_name
from storm.common import sftp
import sys
import threading
import time
import unittest2 as unittest

#test results file
PERF_LOG_FILE = 'nova_api_perf_result.log'
#log levels
DEBUG = 'DEBUG'
INFO = 'INFO'
#configuration files details for test
CONFIG_PATH = os.path.dirname(__file__)
DEFAULT_NOVA_CONF = "nova.conf"
API_PASTE_WITH_DEBUGLOG = "nova-api-paste-with-debuglog.ini"
API_PASTE = "nova-api-paste-without-debuglog.ini"
#service start up wait period (in seconds)
WAIT_TIME = 2


class RequestThread(threading.Thread):
    def __init__(self, api_method, kwargs=None):
        self._api_method = api_method
        self._response = None
        self.kwargs = kwargs
        threading.Thread.__init__(self)

    def run(self):
        """Make the API call and record the response time."""
        if self.kwargs:
            self._response = self._api_method(self.kwargs)
        else:
            self._response = self._api_method()

    def get_response(self):
        return self._response


class NovaPerfTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = storm.config.StormConfig()
        cls.havoc_config = config.HavocConfig()
        #start all the services required by tests.
        cls._start_services()

        cls.os = openstack.Manager()
        cls.client = cls.os.servers_client
        cls.image_ref = cls.config.env.image_ref
        cls.flavor_ref = cls.config.env.flavor_ref
        cls.ssh_timeout = cls.config.nova.ssh_timeout
        #fetch the number of times an API should be hit.
        try:
            cls.perf_api_hit_count = int(cls.config.env.get(
                'perf_api_hit_count', 10))
        except ValueError:
            print "Invalid 'perf_api_hit_count=%s' specified!" % \
                  cls.config.env.get('perf_api_hit_count', '10')
            sys.exit()
        #fetch the thread count.
        try:
            cls.perf_thread_count = int(cls.config.env.get(
                'perf_thread_count', 1))
        except ValueError:
            print "Invalid 'perf_thread_count=%s' specified!" % \
                  cls.config.env.get('perf_thread_count', '1')
            sys.exit()
        #remove the results of the last run.
        if os.path.exists(PERF_LOG_FILE):
            os.remove(PERF_LOG_FILE)
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
    def _start_services(cls):
        run_tests = True

        #fetch the config parameters and verify deploy mode.
        if cls.havoc_config.env.deploy_mode == 'pkg-multi':
            nodes = cls.havoc_config.nodes
            api_mgr = manager.ControllerHavoc(nodes.api.ip, nodes.api.user,
                                                nodes.api.password)
            compute_mgr = manager.ComputeHavoc(nodes.compute.ip,
                                                nodes.compute.user,
                                                nodes.compute.password)
            glance_mgr = manager.GlanceHavoc(nodes.glance.ip,
                            nodes.glance.user,
                            nodes.glance.password,
                            api_config_file="etc/glance-api.conf",
                            registry_config_file="etc/glance-registry.conf")
            scheduler_mgr = manager.ControllerHavoc(nodes.scheduler.ip,
                                                nodes.scheduler.user,
                                                nodes.scheduler.password)
            mysql_mgr = manager.ControllerHavoc(nodes.mysql.ip,
                                                nodes.mysql.user,
                                                nodes.mysql.password)
            rabbitmq_mgr = manager.ControllerHavoc(nodes.rabbitmq.ip,
                                                nodes.rabbitmq.user,
                                                nodes.rabbitmq.password)
            if nodes.keystone:
                keystone_mgr = manager.KeystoneHavoc(nodes.keystone.ip,
                                                nodes.keystone.user,
                                                nodes.keystone.password)
            if nodes.quantum:
                quantum_mgr = manager.QuantumHavoc(nodes.quantum.ip,
                                                nodes.quantum.user,
                                                nodes.quantum.password)
            if nodes.network:
                network_mgr = manager.NetworkHavoc(nodes.network.ip,
                                                nodes.network.user,
                                                nodes.network.password)
        else:
            mgr = manager.ControllerHavoc()
            api_mgr = scheduler_mgr = mysql_mgr = rabbitmq_mgr = mgr

            compute_mgr = manager.ComputeHavoc()
            glance_mgr = manager.GlanceHavoc(
                            api_config_file="etc/glance-api.conf",
                            registry_config_file="etc/glance-registry.conf")
            network_mgr = manager.NetworkHavoc()
            keystone_mgr = manager.KeystoneHavoc()
            quantum_mgr = manager.QuantumHavoc()

        #start all the Nova services.
        mysql_mgr.start_mysql()
        rabbitmq_mgr.start_rabbitmq()
        scheduler_mgr.start_nova_scheduler()
        api_mgr.start_nova_api()

        #start all the Compute services.
        compute_mgr.start_nova_compute()

        #start all the Glance services.
        glance_mgr.start_glance_api()
        glance_mgr.start_glance_registry()

        #determine whether to start Quantum or Network services from nova.conf
        #in the perf_tests directory.
        conf_fp = open(os.path.join(CONFIG_PATH, DEFAULT_NOVA_CONF))
        for line in conf_fp.readlines():
            if line.startswith("--network_manager"):
                if line.find("QuantumManager") != -1:
                    quantum_mgr.start_quantum()
                else:
                    network_mgr.start_nova_network()
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

    def _perf_result_logger(self, result_dict):
        """Log the results to the perf log file."""
        log_list = ["-" * 50,
                    result_dict['api_name'],
                    "WITH_DEBUGLOG\tWITHOUT_DEBUGLOG"]
        sum_t1 = 0
        sum_t2 = 0
        for (t1, t2) in result_dict['results']:
            sum_t1 += float(t1)
            sum_t2 += float(t2)
            log_list.append("%s\t\t%s" % (str(t1), str(t2)))
        test_count = len(result_dict['results'])
        avg_diff = float(sum_t1 / test_count) - float(sum_t2 / test_count)
        log_list.append("Average difference: %.6f" % avg_diff)
        log_str = "\n".join(log_list) + "\n"

        fp = open(PERF_LOG_FILE, "a")
        fp.write(log_str)
        fp.close()

    def _copy_file_to_api_server(self, localpath, remotepath):
        """Copy the specified file to the Nova API server in specified path."""
        if self.havoc_config.env.deploy_mode in ('pkg-multi',
                                                'devstack-remote'):
            #do remote copy.
            api = self.havoc_config.nodes.api
            sftp_session = sftp.Client(api.ip, api.user, api.password)
            return sftp_session.put(localpath, remotepath)
        else:
            #do a local copy.
            try:
                shutil.copy(localpath, remotepath)
                return True
            except IOError:
                return False

    def _create_nova_api_conf(self, log_level=DEBUG, debuglog_enabled=False):
        """Update log level and api-paste config path in nova.conf"""
        #copy the nova.conf file to the API server.
        src = os.path.join(CONFIG_PATH, DEFAULT_NOVA_CONF)
        config_name = "/tmp/nova_perf_test.conf"
        try:
            shutil.copy(src, config_name)
        except IOError:
            self.fail("Failed to copy copy %s to %s" % (src, config_name))

        append_conf = ""
        if log_level == DEBUG:
            append_conf += "--verbose"
        if debuglog_enabled:
            paste_path = os.path.join(CONFIG_PATH, API_PASTE_WITH_DEBUGLOG)
            api_paste_config = os.path.join("/tmp", API_PASTE_WITH_DEBUGLOG)
        else:
            paste_path = os.path.join(CONFIG_PATH, API_PASTE)
            api_paste_config = os.path.join("/tmp", API_PASTE)
        #copy the paste.ini file to the API server.
        status = self._copy_file_to_api_server(paste_path, api_paste_config)
        self.assertTrue(status, "Failure copying configuration file %s to "\
                                    "API server." % src)

        append_conf += "\n--api_paste_config=%s" % api_paste_config
        fp = open(config_name, "a")
        fp.write(append_conf)
        fp.close()

        #copy updated (log level and api-paste config) nova.conf to API server.
        if self.havoc_config.env.deploy_mode in ('pkg-multi',
                                                'devstack-remote'):
            dest_config_name = "/etc/nova/nova.conf"
            status = self._copy_file_to_api_server(config_name,
                                                    dest_config_name)
            self.assertTrue(status, "Failure copying configuration file %s to"\
                                    " API server." % config_name)
        else:
            dest_config_name = config_name
        return dest_config_name

    def _get_api_havoc_mgr(self, config_file=None):
        """Create a ControllerHavoc instance based on the deployment mode."""
        if self.havoc_config.env.deploy_mode in ('pkg-multi',
                                                'devstack-remote'):
            nodes = self.havoc_config.nodes
            mgr = manager.ControllerHavoc(nodes.api.ip, nodes.api.user,
                        nodes.api.password, config_file=config_file)
        else:
            mgr = manager.ControllerHavoc(config_file=config_file)
        return mgr

    def call_list_servers_api(self):
        """Call the List servers API and return response"""
        response = {'status': True, 'response_time': []}
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
        return response

    def _verify_list_servers_api(self, log_level):
        """Verified list servers API for the specified log level."""
        results = []

        mgr = self._get_api_havoc_mgr()
        mgr.stop_nova_api()

        #start the Nova API server in specified log level, with debuglog=True
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=True)
        mgr = self._get_api_havoc_mgr(config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)
        #hit the API
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_list_servers_api))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(self.perf_api_hit_count)
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("List server API %d calls did not complete in %.2f "\
                            "seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("List servers API call failed")
            results.extend(response['response_time'])

        mgr.stop_nova_api()

        #start the Nova API server in specified log level, debuglog=False
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=False)
        mgr = self._get_api_havoc_mgr(config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)
        #hit the API
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_list_servers_api))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        wo_debuglog_results = []
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("List server API %d calls did not complete in %.2f "\
                            "seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("List servers API call failed")
            wo_debuglog_results.extend(response['response_time'])

        for index in range(len(results)):
            results[index] = (results[index], wo_debuglog_results[index])
        return results

    @attr(type='smoke')
    def test_list_servers_loglevel_debug(self):
        """Call List Servers API and log response time."""
        results = self._verify_list_servers_api(log_level=DEBUG)

        #log the results.
        result_dict = {'api_name': 'List Servers API (loglevel=DEBUG)',
                       'results': results}
        self._perf_result_logger(result_dict)

    @attr(type='smoke')
    def test_list_servers_loglevel_info(self):
        """Call List Servers API and log response time."""
        results = self._verify_list_servers_api(log_level=INFO)

        #log the results.
        result_dict = {'api_name': 'List Servers API (loglevel=INFO)',
                       'results': results}
        self._perf_result_logger(result_dict)

    def call_create_servers_api(self):
        """Call the Create servers API and return response"""
        kwargs = {'image_ref': self.image_ref,
                    'flavor_ref': self.flavor_ref}
        response = {'status': True, 'response_time': [], 'server_ids': []}
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
        return response

    def call_delete_servers_api(self, kwargs):
        """Call the Delete servers API and return response"""
        server_ids = kwargs['server_id']

        response = {'status': True, 'response_time': []}
        expected_status = (204, )
        os = openstack.Manager()
        client = os.servers_client
        for server_id in server_ids:
            try:
                resp, body = client.delete_server(server_id)
            except:
                response['status'] = False
                break
            else:
                if resp.status not in expected_status:
                    response['status'] = False
                    break
            response['response_time'].append(client.client.response_time)
        return response

    def _verify_create_delete_server_api(self, log_level):
        """Hit the Create and Delete server API"""
        create_api_results = []
        delete_api_results = []

        mgr = self._get_api_havoc_mgr()
        mgr.stop_nova_api()

        #start the Nova API server in specified log level, with debuglog=True
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=True)
        mgr = self._get_api_havoc_mgr(config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)

        #hit the API
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_create_servers_api))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        thread_timeout = float(self.perf_api_hit_count + 2)
        server_ids = []
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("Create server API %d calls did not complete in "\
                            "%.2f seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("Create servers API call failed")
            create_api_results.extend(response['response_time'])
            server_ids.append(response['server_ids'])

        #make the delete API calls now.
        request_threads = []
        delete_api_expected_status = (204, )
        for index in range(self.perf_thread_count):
            kwargs = {'server_id': server_ids[index]}
            request_threads.append(RequestThread(self.call_delete_servers_api,
                                                kwargs))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("Delete server API %d calls did not complete in "\
                            "%.2f seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("Delete servers API call failed")
            delete_api_results.extend(response['response_time'])

        mgr.stop_nova_api()

        #start the Nova API server in specified log level, debuglog=False
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=False)
        mgr = self._get_api_havoc_mgr(config_file)
        mgr.start_nova_api()
        time.sleep(WAIT_TIME)
        request_threads = []
        for index in range(self.perf_thread_count):
            request_threads.append(RequestThread(self.call_create_servers_api))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        server_ids = []
        create_api_results_wo_debuglog = []
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("Create server API %d calls did not complete in "\
                            "%.2f seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("Create servers API call failed")
            create_api_results_wo_debuglog.extend(response['response_time'])
            server_ids.append(response['server_ids'])

        #store the results for create server API.
        for index in range(len(create_api_results)):
            create_api_results[index] = (create_api_results[index],
                                        create_api_results_wo_debuglog[index])

        #make the delete API calls now.
        request_threads = []
        for index in range(self.perf_thread_count):
            kwargs = {'server_id': server_ids[index]}
            request_threads.append(RequestThread(self.call_delete_servers_api,
                                                kwargs))
            request_threads[index].start() # start making the API requests

        #wait for all the threads to finish requesting.
        delete_api_results_wo_debuglog = []
        for a_thread in request_threads:
            a_thread.join(thread_timeout)
            if a_thread.isAlive():
                self.fail("Delete server API %d calls did not complete in "\
                            "%.2f seconds" % (self.perf_api_hit_count,
                            thread_timeout))
            response = a_thread.get_response()
            if not response['status']:
                self.fail("Delete servers API call failed")
            delete_api_results_wo_debuglog.extend(response['response_time'])

        #store the results for delete server API.
        for index in range(len(delete_api_results)):
            delete_api_results[index] = (delete_api_results[index],
                                        delete_api_results_wo_debuglog[index])

        return create_api_results, delete_api_results

    @attr(type='smoke')
    def test_create_delete_servers_loglevel_debug(self):
        """Call Create and Delete Servers API and log response time."""
        create_perf, delete_perf = self._verify_create_delete_server_api(
            log_level=DEBUG)

        #log the Create API results
        result_dict = {'api_name': 'Create Servers API (loglevel=DEBUG)',
                       'results': create_perf}
        self._perf_result_logger(result_dict)

        #log the Delete API results
        result_dict = {'api_name': 'Delete Servers API (loglevel=DEBUG)',
                       'results': delete_perf}
        self._perf_result_logger(result_dict)

    @attr(type='smoke')
    def test_create_delete_servers_loglevel_info(self):
        """Call Create and Delete Servers API and log response time."""
        create_perf, delete_perf = self._verify_create_delete_server_api(
            log_level=INFO)

        #log the Create API results
        result_dict = {'api_name': 'Create Servers API (loglevel=INFO)',
                       'results': create_perf}
        self._perf_result_logger(result_dict)

        #log the Delete API results
        result_dict = {'api_name': 'Delete Servers API (loglevel=INFO)',
                       'results': delete_perf}
        self._perf_result_logger(result_dict)
