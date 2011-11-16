import json
import storm.common.rest_client as rest_client
import time
import storm.config
from storm import exceptions


class ImagesClient(object):

    def __init__(self, username, key, auth_url, tenant_name, config=None):
        if config is None:
            config = storm.config.StormConfig()
        self.config = config

        self.client = rest_client.RestClient(username, key, auth_url, tenant_name,
                                             config=config)
        self.build_interval = self.config.nova.build_interval
        self.build_timeout = self.config.nova.build_timeout

    def create_image(self, server_id, name, meta = None):
        """
        Creates an image of the original server.
        """

        post_body = {
            'createImage' : {
                'name': name,
            } 
        }

        if meta != None:
            post_body['metadata'] = meta

        post_body = json.dumps(post_body)
        resp, body = self.client.post('servers/%s/action' % 
                                      str(server_id), post_body)
        # Normal response has no content.
        # XXX duplicate of servers_client.create_image
        if int(resp['content-length']) > 0:
            body = json.loads(body)
        return resp, body
        
    def list_images(self, params=None):
        url = 'images'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))
                
            url = "images?" + "".join(param_list)
        
        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body
        
    def list_images_with_detail(self, params=None):
        url = 'images/detail'
        if params != None:
            param_list = []
            for param, value in params.iteritems():
                param_list.append("%s=%s&" % (param, value))
                
            url = "images/detail?" + "".join(param_list)
        
        resp, body = self.client.get(url)
        body = json.loads(body)
        return resp, body
        
    def get_image(self, image_id):
        resp, body = self.client.get("images/%s" % str(image_id))
        body = json.loads(body)
        if resp['status'] == '404':
            raise exceptions.ItemNotFoundException(body['itemNotFound'])
        return resp, body['image']
        
    def delete_image(self, image_id):
        return self.client.delete("images/%s" % str(image_id))

    def wait_for_image_status(self, image_id, status):
        """Waits for an image to reach a given status."""
        resp, body = self.get_image(image_id)
        image_status = body['status']
        start = int(time.time())

        while(image_status != status):
            time.sleep(self.build_interval)
            resp, body = self.get_image(image_id)
            image_status = body['status']

            if(image_status == 'ERROR'):
                raise exceptions.TimeoutException

            if (int(time.time()) - start >= self.build_timeout):
                raise exceptions.BuildErrorException

    def wait_for_image_not_existing(self, image_id):
        """Waits for an image to reach not existing."""
        start = int(time.time())

        while True:
            try:
                resp, body = self.get_image(image_id)
            except exceptions.ItemNotFoundException:
                return

            image_status = body['status']

            if(image_status == 'ERROR'):
                raise exceptions.TimeoutException

            if (int(time.time()) - start >= self.build_timeout):
                raise exceptions.BuildErrorException

            time.sleep(self.build_interval)
