from storm.services.nova.json.images_client import ImagesClient
from storm.services.nova.json.flavors_client import FlavorsClient
from storm.services.nova.json.keypairs_client import KeypairsClient
from storm.services.nova.json.servers_client import ServersClient
from storm.services.keystone.json.keystone_client import KeystoneClient

import storm.config
from storm.services.quantum.json.quantum_client import QuantumClient


class Manager(object):

    def __init__(self, config=None):
        """
        Top level manager for all Openstack APIs
        """

        if config is None:
            config = storm.config.StormConfig()
        self.config = config
        
        if self.config.env.authentication == 'keystone_v2':
            self.servers_client = ServersClient(self.config.nova.username,
                                                self.config.nova.api_key,
                                                self.config.nova.auth_url,
                                                self.config.nova.tenant_name,
                                                config=config)
            self.flavors_client = FlavorsClient(self.config.nova.username,
                                                self.config.nova.api_key,
                                                self.config.nova.auth_url,
                                                self.config.nova.tenant_name,
                                                config=config)
            self.images_client = ImagesClient(self.config.nova.username,
                                              self.config.nova.api_key,
                                              self.config.nova.auth_url,
                                              self.config.nova.tenant_name,
                                              config=config)
            self.keypairs_client = KeypairsClient(self.config.nova.username,
                                                  self.config.nova.api_key,
                                                  self.config.nova.auth_url,
                                                  self.config.nova.tenant_name,
                                                  config=config)
            self.keystone_client = KeystoneClient(self.config.keystone.user,
                                                  self.config.keystone.password,
                                                  self.config.keystone.auth_url,
                                                  self.config.keystone.tenant_name,
                                                  config=config)
            self.quantum_client = QuantumClient(self.config.nova.username,
                                                self.config.nova.api_key,
                                                self.config.nova.auth_url,
                                                self.config.nova.tenant_name,
                                                config=config)
        else:
            #Assuming basic/native authentication
            self.servers_client = ServersClient(self.config.nova.username,
                                                self.config.nova.api_key,
                                                self.config.nova.auth_url)
            self.flavors_client = FlavorsClient(self.config.nova.username,
                                                self.config.nova.api_key,
                                                self.config.nova.auth_url)
            self.images_client = ImagesClient(self.config.nova.username,
                                              self.config.nova.api_key,
                                              self.config.nova.auth_url)
            self.keypairs_client = KeypairsClient(self.config.nova.username,
                                                  self.config.nova.api_key,
                                                  self.config.nova.auth_url)
