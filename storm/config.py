import ConfigParser


class NovaConfig(object):
    """Provides configuration information for connecting to Nova."""

    def __init__(self, conf):
        """Initialize a Nova-specific configuration object"""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("nova", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def auth_url(self):
        """URL used to authenticate. Defaults to 127.0.0.1."""
        return self.get("auth_url", "127.0.0.1")

    @property
    def username(self):
        """Username to use for Nova API requests. Defaults to 'admin'."""
        return self.get("user", "admin")

    @property
    def tenant_name(self):
        """Tenant name to use for Nova API requests. Defaults to 'admin'."""
        return self.get("tenant_name", "admin")

    @property
    def api_key(self):
        """API key to use when authenticating. Defaults to 'admin_key'."""
        return self.get("api_key", "admin_key")

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

    def max_retries(self):
        """Maximum number of times to retry creating a server."""
        return self.get("max_create_server_retries", 5)

    @property
    def host(self):
        """IP address of nova daemon running. Defaults to 127.0.0.1"""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Port number of nova daemon running. Defaults to 8774"""
        return self.get("port", "8774")

    @property
    def directory(self):
        """Directory of nova home. Defaults to /opt/stack/nova"""
        return self.get("directory", "/opt/stack/nova")


class EnvironmentConfig(object):
    def __init__(self, conf):
        """Initialize a Environment-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("environment", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def image_ref(self):
        """Valid imageRef to use """
        return self.get("image_ref", 3)

    @property
    def image_ref_alt(self):
        """Valid imageRef to rebuild images with"""
        return self.get("image_ref_alt", 3)

    @property
    def flavor_ref(self):
        """Valid flavorRef to use"""
        return self.get("flavor_ref", 1)

    @property
    def flavor_ref_alt(self):
        """Valid flavorRef to resize images with"""
        return self.get("flavor_ref_alt", 2)

    @property
    def resize_available(self):
        """ Does the test environment support resizing """
        return self.get("resize_available", 'false') != 'false'

    @property
    def create_image_enabled(self):
        """ Does the test environment support resizing """
        return self.get("create_image_enabled", 'false') != 'false'

    @property
    def authentication(self):
        """ What auth method does the environment use (basic|keystone) """
        return self.get("authentication", 'keystone')


class GlanceConfig(object):
    """Provides configuration information for connecting to Glance."""

    def __init__(self, conf):
        """Initialize a Glance-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("glance", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value


    @property
    def host(self):
        """IP address of keystone daemon running. Defaults to 127.0.0.1"""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Port number of keystone daemon running. Defaults to 9292"""
        return self.get("port", "9292")

    @property
    def directory(self):
        """Directory of Glance home. Defaults to /opt/stack/glance"""
        return self.get("directory", "/opt/stack/glance")

    @property
    def registry_config(self):
        """Path to Glance registry config. Defaults to etc/glance-registry.conf"""
        return self.get("registry_config", "etc/glance-registry.conf")

    @property
    def api_config(self):
        """Path to Glance api config. Defaults to etc/glance-api.conf"""
        return self.get("api_config", "etc/glance-api.conf")


class KeystoneConfig(object):
    """Provides configuration information for connecting to Keystone."""

    def __init__(self, conf):
        """Initialize a keystone-specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("keystone", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def auth_url(self):
        """URL used to authenticate. Defaults to 127.0.0.1."""
        return self.get("auth_url", "127.0.0.1")

    @property
    def host(self):
        """IP address of keystone daemon running. Defaults to 127.0.0.1"""
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        """Port number of keystone daemon running. Defaults to 5000"""
        return self.get("port", "5000")

    @property
    def directory(self):
        """Directory of keystone home. Defaults to /opt/stack/keystone"""
        return self.get("directory", "/opt/stack/keystone")

    @property
    def config(self):
        """Path to keystone registry config. Defaults to etc/keystone.conf"""
        return self.get("config", "etc/keystone.conf")

    @property
    def user(self):
        """Username to use for Keystone API requests. Defaults to 'admin'."""
        return self.get("user", "admin")

    @property
    def tenant_name(self):
        """Tenant name to use for Keystone API requests. Defaults to 'admin'."""
        return self.get("tenant_name", "admin")

    @property
    def password(self):
        """API key to use when authenticating. Defaults to 'admin_key'."""
        return self.get("password", "admin_key")


class QuantumConfig(object):
    """Provides configuration information for connecting to Quantum."""

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

class StormConfig(object):
    """Provides OpenStack configuration information."""

    _path = "etc/storm.conf"

    def __init__(self, path=None):
        """Initialize a configuration from a path."""
        if path is None:
            path = self._path
        self._conf = self.load_config(path)
        self.nova = NovaConfig(self._conf)
        self.env = EnvironmentConfig(self._conf)
        self.glance = GlanceConfig(self._conf)
        self.keystone = KeystoneConfig(self._conf)
        self.quantum = QuantumConfig(self._conf)
        self.mysql = MySQLConfig(self._conf)

    def load_config(self, path=None):
        """Read configuration from given path and return a config object."""
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config
