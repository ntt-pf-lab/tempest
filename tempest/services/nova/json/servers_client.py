from tempest import exceptions
from tempest.common import rest_client
import json
import time


class ServersClient(object):

    def __init__(self, config, username, password, auth_url, tenant_name=None):
        self.config = config
        catalog_type = self.config.compute.catalog_type
        self.client = rest_client.RestClient(config, username, password,
                                             auth_url, catalog_type,
                                             tenant_name)

        self.build_interval = self.config.compute.build_interval
        self.build_timeout = self.config.compute.build_timeout
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}

    def create_server(self, name, image_ref, flavor_ref, **kwargs):
        """
        Creates an instance of a server.
        name (Required): The name of the server.
        image_ref (Required): Reference to the image used to build the server.
        flavor_ref (Required): The flavor used to build the server.
        Following optional keyword arguments are accepted:
        adminPass: Sets the initial root password.
        meta: A dictionary of values to be used as metadata.
        personality: A list of dictionaries for files to be injected into
        the server.
        security_groups: A list of security group dicts.
        networks: A list of network dicts with UUID and fixed_ip.
        user_data: User data for instance.
        availability_zone: Availability zone in which to launch instance.
        accessIPv4: The IPv4 access address for the server.
        accessIPv6: The IPv6 access address for the server.
        min_count: Count of minimum number of instances to launch.
        max_count: Count of maximum number of instances to launch.
        disk_config: Determines if user or admin controls disk configuration.
        """
        post_body = {
            'name': name,
            'imageRef': image_ref,
            'flavorRef': flavor_ref
        }

        for option in ['personality', 'adminPass',
                        'security_groups', 'networks', 'user_data',
                        'availability_zone', 'accessIPv4', 'accessIPv6',
                        'min_count', 'max_count', ('metadata', 'meta'),
                        ('OS-DCF:diskConfig', 'disk_config')]:
            if isinstance(option, tuple):
                post_param = option[0]
                key = option[1]
            else:
                post_param = option
                key = option
            value = kwargs.get(key)
            if value != None:
                post_body[post_param] = value
        post_body = json.dumps({'server': post_body})
        resp, body = self.client.post('servers', post_body, self.headers)

        body = json.loads(body)
        return resp, body['server']

    def update_server(self, server_id, name=None, meta=None, accessIPv4=None,
                      accessIPv6=None):
        """
        Updates the properties of an existing server.
        server_id: The id of an existing server.
        name: The name of the server.
        personality: A list of files to be injected into the server.
        accessIPv4: The IPv4 access address for the server.
        accessIPv6: The IPv6 access address for the server.
        """

        post_body = {}

        if meta != None:
            post_body['metadata'] = meta

        if name != None:
            post_body['name'] = name

        if accessIPv4 != None:
            post_body['accessIPv4'] = accessIPv4

        if accessIPv6 != None:
            post_body['accessIPv6'] = accessIPv6

        post_body = json.dumps({'server': post_body})
        resp, body = self.client.put("servers/%s" % str(server_id),
                                     post_body, self.headers)
#        body = json.loads(body)
#        return resp, body['server']
        if resp['status'] != '200':
            return resp, body
        body = json.loads(body)
        return resp, body['server']

    def get_server(self, server_id):
        """Returns the details of an existing server"""
        resp, body = self.client.get("servers/%s" % str(server_id))
#        body = json.loads(body)
        if resp['status'] != '200' and resp['status'] != '203':
            return resp, body
        body = json.loads(body)
#        if resp['status'] == '404':
#            raise exceptions.ItemNotFoundException(body['itemNotFound'])
        return resp, body['server']

    def delete_server(self, server_id):
        """Deletes the given server"""
        return self.client.delete("servers/%s" % str(server_id))

    def list_servers(self, params=None):
        """Lists all servers for a user"""

        url = 'servers'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "servers?" + "".join(param_list)

        resp, body = self.client.get(url)
        if resp['status'] != '200' and resp['status'] != '203':
            return resp, body
        body = json.loads(body)
        return resp, body

    def list_servers_with_detail(self, params=None):
        """Lists all servers in detail for a user"""

        url = 'servers/detail'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "servers/detail?" + "".join(param_list)

        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body

    def wait_for_server_status(self, server_id, status):
        """Waits for a server to reach a given status"""
        resp, body = self.get_server(server_id)
        if resp['status'] == '404':
            return
        server_status = body['status']
        start = int(time.time())

        while server_status != status:
            time.sleep(self.build_interval)
            resp, body = self.get_server(server_id)
#            if resp['status'] == '404':
#                return
            server_status = body['status']

            if server_status == 'ERROR':
                raise exceptions.BuildErrorException(server_id=server_id)

            if int(time.time()) - start >= self.build_timeout:
                raise exceptions.TimeoutException

    def wait_for_server_not_exists(self, server_id):
        """Waits for a server to reach not existing"""
        start = int(time.time())

        while True:
            resp, body = self.get_server(server_id)
            if resp['status'] == '404':
                return

            server_status = body['status']

            if(server_status == 'ERROR'):
                raise exceptions.TimeoutException

            if (int(time.time()) - start >= self.build_timeout):
                raise exceptions.BuildErrorException

            time.sleep(self.build_interval)

    def wait_for_server_not_exists_ignore_error(self, server_id):
        """Waits for a server to reach not existing"""
        start = int(time.time())

        while True:
            resp, body = self.get_server(server_id)
            if resp['status'] == '404':
                return

            if (int(time.time()) - start >= self.build_timeout):
                raise exceptions.BuildErrorException

            time.sleep(self.build_interval)

    def list_addresses(self, server_id):
        """Lists all addresses for a server"""
        resp, body = self.client.get("servers/%s/ips" % str(server_id))
        body = json.loads(body)
        return resp, body['addresses']

    def list_addresses_by_network(self, server_id, network_id):
        """Lists all addresses of a specific network type for a server"""
        resp, body = self.client.get("servers/%s/ips/%s" %
                                    (str(server_id), network_id))
        body = json.loads(body)
        return resp, body

    def change_password(self, server_id, password):
        """Changes the root password for the server"""
        post_body = {
            'changePassword': {
                'adminPass': password,
            }
        }

        post_body = json.dumps(post_body)
        return self.client.post('servers/%s/action' % str(server_id),
                                post_body, self.headers)

    def reboot(self, server_id, reboot_type):
        """Reboots a server"""
        post_body = {
            'reboot': {
                'type': reboot_type,
            }
        }

        post_body = json.dumps(post_body)
        return self.client.post('servers/%s/action' % str(server_id),
                                post_body, self.headers)

    def rebuild(self, server_id, image_ref, name=None, meta=None,
                personality=None, adminPass=None, disk_config=None):
        """Rebuilds a server with a new image"""
        post_body = {
                'imageRef': image_ref,
        }

        if name != None:
            post_body['name'] = name

        if adminPass != None:
            post_body['adminPass'] = adminPass

        if meta != None:
            post_body['metadata'] = meta

        if personality != None:
            post_body['personality'] = personality

        if disk_config != None:
            post_body['OS-DCF:diskConfig'] = disk_config

        post_body = json.dumps({'rebuild': post_body})
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body,
                                      self.headers)
        body = json.loads(body)
        return resp, body['server']

    def resize(self, server_id, flavor_ref, disk_config=None):
        """Changes the flavor of a server."""
        post_body = {
            'resize': {
                'flavorRef': flavor_ref,
            }
        }

        if disk_config != None:
            post_body['resize']['OS-DCF:diskConfig'] = disk_config

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body, self.headers)
        return resp, body

    def confirm_resize(self, server_id):
        """Confirms the flavor change for a server"""
        post_body = {
            'confirmResize': None,
        }

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body, self.headers)
        return resp, body

    def revert_resize(self, server_id):
        """Reverts a server back to its original flavor"""
        post_body = {
            'revertResize': None,
        }

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body, self.headers)
        return resp, body

    def create_image(self, server_id, image_name, meta=None):
        """Creates an image of the original server"""

        post_body = {
            'createImage': {
                'name': image_name,
            }
        }

        if meta != None:
            post_body['createImage']['metadata'] = meta

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body, self.headers)
        if int(resp['content-length']) > 0:
            body = json.loads(body)
        return resp, body

    def list_server_metadata(self, server_id):
        resp, body = self.client.get("servers/%s/metadata" % str(server_id))
        body = json.loads(body)
        return resp, body['metadata']

    def set_server_metadata(self, server_id, meta):
        post_body = json.dumps({'metadata': meta})
        resp, body = self.client.put('servers/%s/metadata' %
                                     str(server_id), post_body, self.headers)
        body = json.loads(body)
        return resp, body['metadata']

    def update_server_metadata(self, server_id, meta):
        post_body = json.dumps({'metadata': meta})
        resp, body = self.client.post('servers/%s/metadata' %
                                     str(server_id), post_body, self.headers)
        body = json.loads(body)
        return resp, body['metadata']

    def get_server_metadata_item(self, server_id, key):
        resp, body = self.client.get("servers/%s/metadata/%s" %
                                    (str(server_id), key))
        body = json.loads(body)
        return resp, body['meta']

    def set_server_metadata_item(self, server_id, key, meta):
        post_body = json.dumps({'meta': meta})
        resp, body = self.client.put('servers/%s/metadata/%s' %
                                    (str(server_id), key),
                                    post_body, self.headers)
        body = json.loads(body)
        return resp, body['meta']

    def delete_server_metadata_item(self, server_id, key):
        resp, body = self.client.delete("servers/%s/metadata/%s" %
                                    (str(server_id), key))
        return resp, body

    def list_server_virtual_interfaces(self, server_id):
        resp, body = self.client.get("servers/%s/os-virtual-interfaces" %
                                     str(server_id))
        body = json.loads(body)
        return resp, body
