import ConfigParser
import os


class NodeObject(object):
    def __init__(self, value):
        self._set_node_info(value)

    def _set_node_info(self, value):
        node_info = value.split(':')
        self.ip = node_info[0]
        self.user = node_info[1]
        self.password = node_info[2]


class NodesConfig(object):
    """Provides configuration information for connecting to Nova."""

    def __init__(self, conf):
        """Initialize a Node-specific configuration object"""
        self.conf = conf

    def get(self, item_name, default_value=None):
        """Gets the value of specified config parameter"""
        try:
            return self.conf.get("nodes", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    def get_node_list(self, service):
        """Returns a list of node objects"""

        nodes = []
        node_val_list = self.get(service).split(',')
        for value in node_val_list:
            nodes.append(NodeObject(value))

        if len(nodes) <= 1:
            return nodes[0]
        return nodes

    @property
    def api(self):
        return self.get_node_list("api")

    @property
    def compute(self):
        return self.get_node_list("compute")

    @property
    def network(self):
        return self.get_node_list("network")

    @property
    def volume(self):
        return self.get_node_list("volume")

    @property
    def glance(self):
        return self.get_node_list("glance")

    @property
    def swift(self):
        return self.get_node_list("swift")

    @property
    def mysql(self):
        return self.get_node_list("mysql")

    @property
    def rabbitmq(self):
        return self.get_node_list("rabbitmq")

    @property
    def ssh_timeout(self):
        return self.get("ssh_timeout")


class ServicesConfig(object):
    """Provides configuration information for dependent services"""

    def __init__(self, conf):
        """Initialize a Services specific configuration object."""
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("services", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def mysql_user(self):
        return self.get("mysql_user", "root")

    @property
    def mysql_pass(self):
        return self.get("mysql_pass", "nova")

    @property
    def rabbit_user(self):
        return self.get("rabbit_user", "guest")

    @property
    def rabbit_pass(self):
        return self.get("rabbit_pass", "guest")


class EnvironmentConfig(object):
    """Global properties for Stackmonkey"""

    def __init__(self, conf):
        self.conf = conf

    def get(self, item_name, default_value):
        try:
            return self.conf.get("environment", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def deploy_mode(self):
        return self.get("deploy_mode", "pkg-multi")

    @property
    def devstack_root(self):
	return self.get("devstack_root", "/opt/stack")

    @property
    def devstack_host(self):
        return self.get("devstack_host", "localhost")


class HavocConfig(object):
    """Provides OpenStack multi-node configuration"""

    DEFAULT_CONFIG_DIR = os.path.join(
            os.path.abspath(
                os.path.dirname(
                    os.path.dirname(__file__))),
                "etc")

    DEFAULT_CONFIG_FILE = "havoc.conf"

    def __init__(self):
        """Initialize a configuration from a path."""

        # Environment variables override defaults...
        conf_dir = os.environ.get('TEMPEST_CONFIG_DIR',
            self.DEFAULT_CONFIG_DIR)
        conf_file = os.environ.get('TEMPEST_CONFIG',
            self.DEFAULT_CONFIG_FILE)

        path = os.path.join(conf_dir, conf_file)

        path = 'havoc.conf'
        if not os.path.exists(path):
            msg = "Config file %(path) not found" % locals()
            raise RuntimeError(msg)


        self._conf = self.load_config(path)
        self.nodes = NodesConfig(self._conf)
        self.services = ServicesConfig(self._conf)
        self.env = EnvironmentConfig(self._conf)

    def load_config(self, path=None):
        """Read configuration from given path and return a config object."""
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config
