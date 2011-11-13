import subprocess
import time
import urllib
from nose.plugins.attrib import attr
from storm import openstack
from storm.common.utils.data_utils import rand_name
import base64
import medium.config
import unittest2 as unittest


def wait_to_be_launched(host, port):
    while True:
        try:
            urllib.urlopen('http://%(host)s:%(port)s/' % locals())
            time.sleep(.1)
            break
        except IOError:
            pass


class GlanceRegistryProcess(object):
    def __init__(self, directory, config):
        self.directory = directory
        self.config = config
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/glance-registry",
                                          "--config-file=%s" % self.config],
                                         cwd=self.directory)
        assert self._process.returncode is None

    def stop(self):
        self._process.terminate()
        self._process = None


class GlanceApiProcess(object):
    def __init__(self, directory, config, host, port):
        self.directory = directory
        self.config = config
        self.host = host
        self.port = port
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/glance-api",
                                          "--config-file=%s" % self.config],
                                         cwd=self.directory)
        assert self._process.returncode is None
        wait_to_be_launched(self.host, self.port)

    def stop(self):
        self._process.terminate()
        self._process = None


class KeystoneProcess(object):
    def __init__(self, directory, config, host, port):
        self.directory = directory
        self.config = config
        self.host = host
        self.port = port
        self._process = None

    def start(self):
        self._process = subprocess.Popen(["bin/keystone",
                                          "--config-file", self.config,
                                          "-d"],
                                         cwd=self.directory)
        assert self._process.returncode is None
        wait_to_be_launched(self.host, self.port)

    def stop(self):
        self._process.terminate()
        self._process = None


class ServersTest(unittest.TestCase):

    config_path = 'etc/medium.config.ini'

    @classmethod
    def setUpClass(cls):
        cls.config = medium.config.MediumConfig(cls.config_path)

        # boot glance.
        cls.glance_registry = GlanceRegistryProcess(
                cls.config.glance.directory,
                cls.config.glance.registry_config)
        cls.glance_api = GlanceApiProcess(
                cls.config.glance.directory,
                cls.config.glance.api_config,
                cls.config.glance.host,
                cls.config.glance.port)
        cls.glance_registry.start()
        cls.glance_api.start()

        # boot keystone.
        cls.keystone = KeystoneProcess(
                cls.config.keystone.directory,
                cls.config.keystone.config,
                cls.config.keystone.host,
                cls.config.keystone.port)
        cls.keystone.start()

        # cls.os = openstack.Manager()
        # cls.client = cls.os.servers_client
        # cls.image_ref = cls.config.env.image_ref
        # cls.flavor_ref = cls.config.env.flavor_ref
        # cls.ssh_timeout = cls.config.nova.ssh_timeout

    @classmethod
    def tearDownClass(cls):
        cls.glance_registry.stop()
        cls.glance_api.stop()
        cls.keystone.stop()

    @attr(type='smoke')
    def test_through(self):
        pass
        """
        meta = {'hello': 'world'}
        accessIPv4 = '1.1.1.1'
        accessIPv6 = '::babe:220.12.22.2'
        name = rand_name('server')
        file_contents = 'This is a test file.'
        personality = [{'path': '/etc/test.txt',
                       'contents': base64.b64encode(file_contents)}]
        resp, server = self.client.create_server(name,
                                                 self.image_ref,
                                                 self.flavor_ref,
                                                 meta=meta,
                                                 accessIPv4=accessIPv4,
                                                 accessIPv6=accessIPv6,
                                                 personality=personality)

        #Wait for the server to become active
        self.client.wait_for_server_status(server['id'], 'ACTIVE')

        #Verify the specified attributes are set correctly
        resp, server = self.client.get_server(server['id'])
        self.assertEqual('1.1.1.1', server['accessIPv4'])
        self.assertEqual('::babe:220.12.22.2', server['accessIPv6'])
        self.assertEqual(name, server['name'])
        self.assertEqual(self.image_ref, server['image']['id'])
        self.assertEqual(str(self.flavor_ref), server['flavor']['id'])

        #Teardown
        self.client.delete_server(self.id)
        """
