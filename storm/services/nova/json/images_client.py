from storm import exceptions
from storm.common import rest_client
import json
import storm.config
import time


class ImagesClient(object):

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

    def create_image(self, server_id, name, meta=None):
        """Creates an image of the original server"""

        post_body = {
            'createImage': {
                'name': name,
            }
        }

        if meta != None:
            post_body['createImage']['metadata'] = meta

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' %
                                      str(server_id), post_body, self.headers)
        # Normal response has no content.
        # XXX duplicate of servers_client.create_image
        if int(resp['content-length']) > 0:
            body = json.loads(body)
        return resp, body

    def list_images(self, params=None):
        """Returns a list of all images filtered by any parameters"""
        url = 'images'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "images?" + "".join(param_list)

        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body['images']

    def list_images_with_detail(self, params=None):
        """Returns a detailed list of images filtered by any parameters"""
        url = 'images/detail'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))

            url = "images/detail?" + "".join(param_list)

        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body['images']

    def get_image(self, image_id):
        """Returns the details of a single image"""
        resp, body = self.client.get("images/%s" % str(image_id))
        body = json.loads(body)
        if resp['status'] == '404':
            return resp, body
        return resp, body['image']

    def delete_image(self, image_id):
        """Deletes the provided image"""
        return self.client.delete("images/%s" % str(image_id))

    def wait_for_image_exists(self, image_id):
        resp, body = self.client.get("images/%s" % str(image_id))
        start = int(time.time())

        while resp.status != 200:
            time.sleep(self.build_interval)
            resp, body = self.client.get("images/%s" % str(image_id))

            if int(time.time()) - start >= self.build_timeout:
                raise exceptions.BuildErrorException

    def wait_for_image_status(self, image_id, status):
        """Waits for an image to reach a given status"""
        resp, image = self.get_image(image_id)
        start = int(time.time())

        while image['status'] != status:
            time.sleep(self.build_interval)
            resp, image = self.get_image(image_id)

            if image['status'] == 'ERROR':
                raise exceptions.TimeoutException

            if int(time.time()) - start >= self.build_timeout:
                raise exceptions.BuildErrorException

    def wait_for_image_not_exists(self, image_id):
        """Waits for an image to reach not exists"""
        start = int(time.time())

        while True:
            resp, image = self.get_image(image_id)
            if resp['status'] == '404':
                return
            elif image['status'] == 'ERROR':
                raise exceptions.TimeoutException

            if int(time.time()) - start >= self.build_timeout:
                raise exceptions.BuildErrorException

            time.sleep(self.build_interval)

    def list_image_metadata(self, image_id):
        resp, body = self.client.get("images/%s/metadata" % str(image_id))
        body = json.loads(body)
        return resp, body

    def set_image_metadata(self, image_id, meta):
        post_body = json.dumps({'metadata': meta})
        resp, body = self.client.put('images/%s/metadata' %
                                      str(image_id), post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def update_image_metadata(self, image_id, meta):
        post_body = json.dumps({'metadata': meta})
        resp, body = self.client.post('images/%s/metadata' %
                                      str(image_id), post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def get_image_metadata_item(self, image_id, key):
        resp, body = self.client.get("images/%s/metadata/%s" %
                                     (str(image_id), key))
        body = json.loads(body)
        return resp, body

    def set_image_metadata_item(self, image_id, key, meta):
        post_body = json.dumps({'meta': meta})
        resp, body = self.client.put('images/%s/metdata/%s' %
                                     (str(image_id), key),
                                     post_body, self.headers)
        body = json.loads(body)
        return resp, body

    def delete_image_metadata_item(self, image_id, key):
        resp, body = self.client.delete("images/%s/metadata/%s" %
                                     (str(image_id), key))
        return resp, body
