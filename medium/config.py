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


class MediumConfig(config.StormConfig):
    def __init__(self, path="etc/medium.conf"):
        super(MediumConfig, self).__init__(path)
        self.glance = GlanceConfig(self._conf)
