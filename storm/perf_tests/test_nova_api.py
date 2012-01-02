from nose.plugins.attrib import attr
import os
import shutil
from stackmonkey import manager
from storm import openstack
import storm.config
from storm.common.utils.data_utils import rand_name
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


class NovaPerfTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.os = openstack.Manager()
        cls.client = cls.os.servers_client
        cls.config = storm.config.StormConfig()
        cls.image_ref = cls.config.env.image_ref
        cls.flavor_ref = cls.config.env.flavor_ref
        cls.ssh_timeout = cls.config.nova.ssh_timeout
        #remove the results of the last run.
        os.remove(PERF_LOG_FILE)

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

    def _create_nova_api_conf(self, log_level=DEBUG, debuglog_enabled=False):
        """Update log level and api-paste config path in nova.conf"""
        src = os.path.join(CONFIG_PATH, DEFAULT_NOVA_CONF)
        config_name = "/tmp/nova_perf_test.conf"
        shutil.copy(src, config_name)

        append_conf = ""
        if log_level == DEBUG:
            append_conf += "--verbose"
        if debuglog_enabled:
            api_paste_config = os.path.join(CONFIG_PATH,
                                            API_PASTE_WITH_DEBUGLOG)
        else:
            api_paste_config = os.path.join(CONFIG_PATH,
                                            API_PASTE)
        append_conf += "\n--api_paste_config=%s" % api_paste_config
        fp = open(config_name, "a")
        fp.write(append_conf)
        fp.close()
        return config_name

    def _verify_list_servers_api(self, log_level):
        """Verified list servers API for the specified log level."""
        results = []

        mgr = manager.ControllerHavoc()
        mgr.stop_nova_api()

        #start the Nova API server in specified log level, with debuglog=True
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=True)
        mgr = manager.ControllerHavoc(config_file=config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)
        #hit the API
        for i in range(10):
            resp, body = self.client.list_servers()
            results.append([self.client.client.response_time])

        mgr.stop_nova_api()

        #start the Nova API server in specified log level, debuglog=False
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=False)
        mgr = manager.ControllerHavoc(config_file=config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)
        #hit the API
        for i in range(10):
            resp, body = self.client.list_servers()
            results[i].append(self.client.client.response_time)
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

    def _verify_create_delete_server_api(self, log_level):
        """Hit the Create and Delete server API"""
        create_api_results = []
        delete_api_results = []

        mgr = manager.ControllerHavoc()
        mgr.stop_nova_api()

        #start the Nova API server in specified log level, with debuglog=True
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=True)
        mgr = manager.ControllerHavoc(config_file=config_file)
        mgr.start_nova_api()
        #wait for service to get started
        time.sleep(WAIT_TIME)

        #hit the API
        for i in range(10):
            name = rand_name('server')
            resp, body = self.client.create_server(name,
                                                   self.image_ref,
                                                   self.flavor_ref)
            create_api_results.append([self.client.client.response_time])
            self.client.delete_server(body['id'])
            delete_api_results.append([self.client.client.response_time])

        mgr.stop_nova_api()

        #start the Nova API server in specified log level, debuglog=False
        config_file = self._create_nova_api_conf(log_level=log_level,
                                                 debuglog_enabled=False)
        mgr = manager.ControllerHavoc(config_file=config_file)
        mgr.start_nova_api()
        time.sleep(WAIT_TIME)
        for i in range(10):
            name = rand_name('server')
            resp, body = self.client.create_server(name,
                                                   self.image_ref,
                                                   self.flavor_ref)
            create_api_results[i].append(self.client.client.response_time)
            self.client.delete_server(body['id'])
            delete_api_results[i].append(self.client.client.response_time)
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
