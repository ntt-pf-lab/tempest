from storm import exceptions
from storm.common import rest_client
import json
import storm.config
import time


class KeypairsClient(object):

    def __init__(self, username, key, auth_url, tenant_name, config=None):
        if config is None:
            config = storm.config.StormConfig()
        self.config = config

        self.client = rest_client.RestClient(username, key,
                                             auth_url, tenant_name,
                                             config=config)
        self.build_interval = self.config.nova.build_interval
        self.build_timeout = self.config.nova.build_timeout
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}

    def create_keypair(self, keyname):
        """
        Creates a keypair.
        keyname: The name of the keypair.
        """

        post_body = {
            'name': keyname,
        }

        post_body = json.dumps({'keypair': post_body})
        resp, body = self.client.post('os-keypairs', post_body, self.headers)
        body = json.loads(body)
        return resp, body['keypair']

    def list_keypairs(self):
        """Lists all keypairs"""

        resp, body = self.client.get('os-keypairs')
        body = json.loads(body)
        return resp, body['keypairs']

    def delete_keypair(self, keyname):
        """Deletes the given keypair"""
        return self.client.delete("os-keypairs/%s" % str(keyname))
