# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ConfigParser
import logging
import os

from tempest.common.utils import data_utils

LOG = logging.getLogger(__name__)


class BaseConfig(object):

    SECTION_NAME = None

    def __init__(self, conf):
        self.conf = conf

    def get(self, item_name, default_value=None):
        try:
            return self.conf.get(self.SECTION_NAME, item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value


class IdentityConfig(BaseConfig):

    """
    Provides configuration information for authenticating with Keystone.
    """

    SECTION_NAME = "identity"

    @property
    def host(self):
        """Host IP for making Identity API requests."""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Port for the Identity Service API."""
        return self.get("port", "5000")

    @property
    def api_version(self):
        """Version of the Identity API"""
        return self.get("api_version", "v1.1")

    @property
    def path(self):
        """Path of API request"""
        return self.get("path", "/")

    @property
    def use_ssl(self):
        """Specifies if we are using https."""
        return self.get("use_ssl", 'false').lower() != 'false'

    @property
    def auth_url(self):
        """The Identity URL (derived)"""
        auth_url = data_utils.build_url(self.host,
                                        self.port,
                                        api_version=self.api_version,
                                        path=self.path,
                                        use_ssl=self.use_ssl)
        return auth_url

    @property
    def strategy(self):
        """Which auth method does the environment use? (basic|keystone)"""
        return self.get("strategy", 'keystone')

    @property
    def source_dir(self):
        """Directory of keystone home. Defaults to /opt/stack/keystone"""
        return self.get("source_dir", "/opt/stack/keystone")

    @property
    def config(self):
        """Path to keystone registry config. Defaults to etc/keystone.conf"""
        return self.get("config", "etc/keystone.conf")


class ComputeConfig(BaseConfig):

    SECTION_NAME = "compute"

    @property
    def username(self):
        """Username to use for Nova API requests."""
        return self.get("username", "demo")

    @property
    def tenant_name(self):
        """Tenant name to use for Nova API requests."""
        return self.get("tenant_name", "demo")

    def tenant_id(self):
        """Tenant id to use for Nova API requests. Defaults to 'admin'."""
        return self.get("tenant_id", "admin")

    @property
    def password(self):
        """API key to use when authenticating."""
        return self.get("password", "pass")

    @property
    def alt_username(self):
        """Username of alternate user to use for Nova API requests."""
        return self.get("alt_username")

    @property
    def alt_tenant_name(self):
        """Alternate user's Tenant name to use for Nova API requests."""
        return self.get("alt_tenant_name")

    def alt_password(self):
        """API key to use when authenticating as alternate user."""
        return self.get("alt_password")

    @property
    def image_ref(self):
        """Valid primary image to use in tests."""
        return self.get("image_ref", "{$IMAGE_ID}")

    @property
    def image_ref_alt(self):
        """Valid secondary image reference to be used in tests."""
        return self.get("image_ref_alt", "{$IMAGE_ID_ALT}")

    @property
    def flavor_ref(self):
        """Valid primary flavor to use in tests."""
        return self.get("flavor_ref", 1)

    @property
    def flavor_ref_alt(self):
        """Valid secondary flavor to be used in tests."""
        return self.get("flavor_ref_alt", 2)

    @property
    def resize_available(self):
        """Does the test environment support resizing?"""
        return self.get("resize_available", 'false').lower() != 'false'

    @property
    def create_image_enabled(self):
        """Does the test environment support snapshots?"""
        return self.get("create_image_enabled", 'false').lower() != 'false'

    @property
    def build_interval(self):
        """Time in seconds between build status checks."""
        return float(self.get("build_interval", 10))

    @property
    def build_timeout(self):
        """Timeout in seconds to wait for an entity to build."""
        return float(self.get("build_timeout", 300))

    @property
    def catalog_type(self):
        """Catalog type of the Compute service."""
        return self.get("catalog_type", 'compute')

    @property
    def source_dir(self):
        """Directory of nova home. Defaults to /opt/stack/nova"""
        return self.get("source_dir", "/opt/stack/nova")

    @property
    def config(self):
        """path of nova.conf. Defaults to /opt/stack/nova/etc/nova.conf"""
        return self.get("config", "/opt/stack/nova/etc/nova.conf")

    def log_level(self):
        """Level for logging compute API calls."""
        return self.get("log_level", 'ERROR')


class ComputeAdminConfig(BaseConfig):

    """
    Provides configuration information for administrative usage of the Compute
    API.
    """

    SECTION_NAME = "compute-admin"

    @property
    def username(self):
        """Administrative Username to use for Nova API requests."""
        return self.get("username", "admin")

    @property
    def tenant_name(self):
        """Administrative Tenant name to use for Nova API requests."""
        return self.get("tenant_name", "admin")

    @property
    def password(self):
        """API key to use when authenticating as admin."""
        return self.get("password", "admimpass")


class IdentityAdminConfig(IdentityConfig):

    """
    Provides configuration information for the administrative usage of the
    Identity API.
    """

    SECTION_NAME = "identity-admin"

    @property
    def username(self):
        """Username to use for Identity administrative API requests. Defaults
        to 'key_admin'."""
        return self.get("username", "key_admin")

    @property
    def tenant_name(self):
        """Tenant name of administrative user."""
        return self.get("tenant_name", "admin")

    @property
    def password(self):
        """Password of administrative user."""
        return self.get("password", "admimpass")

    @property
    def port(self):
        """Port for the Identity Admin API"""
        return self.get("port", "35357")

    @property
    def api_version(self):
        """Version of the Identity API"""
        return self.get("api_version", "v1.1")


class ImagesConfig(BaseConfig):

    """
    Provides configuration information for connecting to an
    OpenStack Images service.
    """

    SECTION_NAME = "image"

    @property
    def host(self):
        """Host IP for making Images API requests. Defaults to '127.0.0.1'."""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Listen port of the Images service."""
        return int(self.get("port", "9292"))

    @property
    def api_version(self):
        """Version of the API"""
        return self.get("api_version", "1")

    @property
    def username(self):
        """Username to use for Images API requests. Defaults to 'demo'."""
        return self.get("user", "demo")

    @property
    def password(self):
        """Password for user"""
        return self.get("password", "pass")

    @property
    def tenant_name(self):
        """Tenant to use for Images API requests. Defaults to 'demo'."""
        return self.get("tenant_name", "demo")


# TODO(jaypipes): Move this to a common utils (not data_utils...)
def singleton(cls):
    """Simple wrapper for classes that should only have a single instance"""
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

    @property
    def source_dir(self):
        """Directory of Images service home. Defaults to /opt/stack/glance"""
        return self.get("source_dir", "/opt/stack/glance")

    @property
    def registry_config(self):
        """Path to Images registry config.
        Defaults to etc/glance-registry.conf"""
        return self.get("registry_config", "etc/glance-registry.conf")

    @property
    def api_config(self):
        """Path to Images api config. Defaults to etc/glance-api.conf"""
        return self.get("api_config", "etc/glance-api.conf")


class NetworkConfig(object):
    """Provides configuration information for connecting to an
    OpenStack Network Service.
    """

    def __init__(self, conf):
        """Initialize a quantum-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("network", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def source_dir(self):
        """Directory of quantum home. Defaults to /opt/stack/quantum"""
        return self.get("source_dir", "/opt/stack/quantum")

    @property
    def config(self):
        """Path to quantum manager config. Defaults to etc/quantum.conf"""
        return self.get("config", "etc/quantum.conf")

    @property
    def agent_config(self):
        """Path to quantum agent plugin config.
        Defaults to quantum/plugins/openvswitch/ovs_quantum_plugin.ini"""
        return self.get("agent_config",
                "quantum/plugins/openvswitch/ovs_quantum_plugin.ini")

    @property
    def api_version(self):
        """Version of Quantum API"""
        return self.get("api_version", "v1.0")


class MySQLConfig(object):
    """Provides configuration information for connecting to MySQL."""

    def __init__(self, conf):
        """Initialize a mysql-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("mysql", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def user(self):
        """Username of MySQL service"""
        return self.get('user', 'root')

    @property
    def password(self):
        """Password for MySQL user"""
        return self.get('password', 'password')

    @property
    def host(self):
        """MySQL service host"""
        return self.get('host', 'localhost')


@singleton
class TempestConfig:
    """Provides OpenStack configuration information."""

    DEFAULT_CONFIG_DIR = os.path.join(
        os.path.abspath(
          os.path.dirname(
            os.path.dirname(__file__))),
        "etc")

    DEFAULT_CONFIG_FILE = "tempest.conf"

    def __init__(self):
        """Initialize a configuration from a conf directory and conf file."""

        # Environment variables override defaults...
        conf_dir = os.environ.get('TEMPEST_CONFIG_DIR',
            self.DEFAULT_CONFIG_DIR)
        conf_file = os.environ.get('TEMPEST_CONFIG',
            self.DEFAULT_CONFIG_FILE)

        path = os.path.join(conf_dir, conf_file)
        print path

        LOG.info("Using tempest config file %s" % path)

        if not os.path.exists(path):
            msg = "Config file %(path)s not found" % locals()
            raise RuntimeError(msg)

        self._conf = self.load_config(path)
        self.identity = IdentityConfig(self._conf)
        self.compute = ComputeConfig(self._conf)
        self.compute_admin = ComputeAdminConfig(self._conf)
        self.identity_admin = IdentityAdminConfig(self._conf)
        self.images = ImagesConfig(self._conf)
        self.network = NetworkConfig(self._conf)
        self.mysql = MySQLConfig(self._conf)

    def load_config(self, path):
        """Read configuration from given path and return a config object."""
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config
