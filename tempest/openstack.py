import tempest.config
from tempest import exceptions
from tempest.services.image import service as image_service
from tempest.services.nova.json.images_client import ImagesClient
from tempest.services.nova.json.flavors_client import FlavorsClient
from tempest.services.nova.json.servers_client import ServersClient
from tempest.services.nova.json.limits_client import LimitsClient
from tempest.services.nova.json.extensions_client import ExtensionsClient
from tempest.services.nova.json.security_groups_client \
import SecurityGroupsClient
from tempest.services.nova.json.floating_ips_client import FloatingIPsClient
from tempest.services.nova.json.keypairs_client import KeyPairsClient
from tempest.services.quantum.json.quantum_client import QuantumClient
from tempest.services.nova.json.volumes_client import VolumesClient


class Manager(object):

    def __init__(self, username=None, password=None, tenant_name=None):
        """
        Top level manager for all Openstack APIs
        """
        self.config = tempest.config.TempestConfig()

        if None in [username, password, tenant_name]:
            # Pull from the default, the first non-admin user
            username = self.config.identity.nonadmin_user1
            password = self.config.identity.nonadmin_user1_password
            tenant_name = self.config.identity.nonadmin_user1_tenant_name

        if None in [username, password, tenant_name]:
            # We can't find any usable credentials, fail early
            raise exceptions.InvalidConfiguration(message="Missing complete \
                                                  user credentials.")
        auth_url = self.config.identity.auth_url

        if self.config.identity.strategy == 'keystone':
            client_args = (self.config, username, password, auth_url,
                           tenant_name)
        else:
            client_args = (self.config, username, password, auth_url)

        self.servers_client = ServersClient(*client_args)
        self.flavors_client = FlavorsClient(*client_args)
        self.images_client = ImagesClient(*client_args)
        self.limits_client = LimitsClient(*client_args)
        self.extensions_client = ExtensionsClient(*client_args)
        self.keypairs_client = KeyPairsClient(*client_args)
        self.security_groups_client = SecurityGroupsClient(*client_args)
        self.floating_ips_client = FloatingIPsClient(*client_args)
        self.networks_client = QuantumClient(*client_args)
        self.volumes_client = VolumesClient(*client_args)


class ServiceManager(object):

    """
    Top-level object housing clients for OpenStack APIs
    """

    def __init__(self):
        self.config = tempest.config.TempestConfig()
        self.services = {}
        self.services['image'] = image_service.Service(self.config)
        self.images = self.services['image']
