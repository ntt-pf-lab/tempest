import ConfigParser
from storm import config


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


class MediumConfig(config.StormConfig):
    def __init__(self, path="etc/medium.conf"):
        super(MediumConfig, self).__init__(path)
        self.glance = GlanceConfig(self._conf)
        self.keystone = KeystoneConfig(self._conf)
        self.quantum = QuantumConfig(self._conf)
