import ConfigParser
import logging
import os
from tempest.common.utils import data_utils

LOG = logging.getLogger(__name__)


class IdentityConfig(object):
    """Provides configuration information for authenticating with Keystone."""

    def __init__(self, conf):
        """Initialize an Identity-specific configuration object"""
        self.conf = conf

    def get(self, item_name, default_value=None):
        try:
            return self.conf.get("identity", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def host(self):
        """Host IP for making Identity API requests."""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Port for the Identity service."""
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
    def auth_url(self):
        """The Identity URL (derived)"""
        auth_url = data_utils.build_url(self.host,
                                        self.port,
                                        self.api_version,
                                        self.path,
                                        use_ssl=self.use_ssl)
        return auth_url

    @property
    def use_ssl(self):
        """Specifies if we are using https."""
        return self.get("use_ssl", 'false').lower() != 'false'

    @property
    def nonadmin_user1(self):
        """Username to use for Nova API requests."""
        return self.get("nonadmin_user1")

    @property
    def nonadmin_user1_tenant_name(self):
        """Tenant name to use for Nova API requests."""
        return self.get("nonadmin_user1_tenant_name")

    @property
    def nonadmin_user1_password(self):
        """API key to use when authenticating."""
        return self.get("nonadmin_user1_password")

    @property
    def nonadmin_user2(self):
        """Alternate username to use for Nova API requests."""
        return self.get("nonadmin_user2")

    @property
    def nonadmin_user2_tenant_name(self):
        """Alternate tenant name for Nova API requests."""
        return self.get("nonadmin_user2_tenant_name")

    @property
    def nonadmin_user2_password(self):
        """Alternate API key to use when authenticating."""
        return self.get("nonadmin_user2_password")

    @property
    def strategy(self):
        """Which auth method does the environment use? (basic|keystone)"""
        return self.get("strategy", 'keystone')

    @property
    def directory(self):
        """Directory of keystone home. Defaults to /opt/stack/keystone"""
        return self.get("directory", "/opt/stack/keystone")

    @property
    def config(self):
        """Path to keystone registry config. Defaults to etc/keystone.conf"""
        return self.get("config", "etc/keystone.conf")


class ComputeConfig(object):
    def __init__(self, conf):
        """Initialize a Compute-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("compute", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def image_ref(self):
        """Valid primary image to use in tests."""
        return self.get("image_ref", 'e7ddc02e-92fa-4f82-b36f-59b39bf66a67')

    @property
    def image_ref_alt(self):
        """Valid secondary image reference to be used in tests."""
        return self.get("image_ref_alt", '346f4039-a81e-44e0-9223-4a3d13c907')

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
    def release_name(self):
        """Which release is this?"""
        return self.get("release_name", 'essex')

    @property
    def build_interval(self):
        """Time in seconds between build status checks."""
        return float(self.get("build_interval", 10))

    @property
    def ssh_timeout(self):
        """Timeout in seconds to use when connecting via ssh."""
        return float(self.get("ssh_timeout", 300))

    @property
    def build_timeout(self):
        """Timeout in seconds to wait for an entity to build."""
        return float(self.get("build_timeout", 300))

    @property
    def catalog_type(self):
        """Catalog type of the Compute service."""
        return self.get("catalog_type", 'compute')

    @property
    def directory(self):
        """Directory of nova home. Defaults to /opt/stack/nova"""
        return self.get("directory", "/opt/stack/nova")

    @property
    def config(self):
        """path of nova.conf. Defaults to /opt/openstack/nova/etc/nova.conf"""
        return self.get("config", "/opt/openstack/nova/etc/nova.conf")


class ImagesConfig(object):
    """
    Provides configuration information for connecting to an
    OpenStack Images service.
    """

    def __init__(self, conf):
        self.conf = conf

    def get(self, item_name, default_value=None):
        try:
            return self.conf.get("image", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

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
        """Username to use for Images API requests. Defaults to 'admin'."""
        return self.get("user", "admin")

    @property
    def password(self):
        """Password for user"""
        return self.get("password", "")

    @property
    def tenant(self):
        """Tenant to use for Images API requests. Defaults to 'admin'."""
        return self.get("tenant", "admin")

    @property
    def service_token(self):
        """Token to use in querying the API. Default: None"""
        return self.get("service_token")

    @property
    def auth_url(self):
        """Optional URL to auth service. Will be discovered if None"""
        return self.get("auth_url")

    @property
    def directory(self):
        """Directory of Images service home. Defaults to /opt/stack/glance"""
        return self.get("directory", "/opt/stack/glance")

    @property
    def registry_config(self):
        """Path to Images registry config. Defaults to etc/glance-registry.conf"""
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
            return self.conf.get("quantum", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def directory(self):
        """Directory of quantum home. Defaults to /opt/stack/quantum"""
        return self.get("directory", "/opt/stack/quantum")

    @property
    def config(self):
        """Path to quantum manager config. Defaults to etc/quantum.conf"""
        return self.get("config", "etc/quantum.conf")

    @property
    def agent_config(self):
        """Path to quantum agent plugin config. Defaults to quantum/plugins/openvswitch/ovs_quantum_plugin.ini"""
        return self.get("agent_config", "quantum/plugins/openvswitch/ovs_quantum_plugin.ini")


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
        return self.get('user', 'root')

    @property
    def password(self):
        return self.get('password', 'password')

    @property
    def host(self):
        return self.get('host', 'localhost')


class TempestConfig(object):
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

        if not os.path.exists(path):
            msg = "Config file %(path)s not found" % locals()
            raise RuntimeError(msg)

        self._conf = self.load_config(path)
        self.identity = IdentityConfig(self._conf)
	self.compute = ComputeConfig(self._conf)
        self.images = ImagesConfig(self._conf)
	self.network = NetworkConfig(self._conf)
        self.mysql = MySQLConfig(self._conf)

    def load_config(self, path):
        """Read configuration from given path and return a config object."""
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config
