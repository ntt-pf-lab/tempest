#!/usr/bin/env python
import logging
import argparse
import json
import uuid

from bottle import abort, get, post, put, delete, request, HTTPResponse


def get_parser():
    parser = argparse.ArgumentParser()

    # server configures.
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=9696)
    parser.add_argument('-d', '--debug', action='store_true')

    # tenant ids to fake as it exists.
    parser.add_argument('--tenant', action='append')

    # rest api configures.
    # the optional value of each api below is http status code
    # which will override default response.
    for option_name in ('create_network',
                        'delete_network',
                        'show_network_details',
                        'list_networks',
                        'create_port',
                        'delete_port',
                        'list_ports',
                        'plug_port_attachment',
                        'unplug_port_attachment',
                        'show_port_attachment',
                        ):
        parser.add_argument('--%s' % option_name, type=int,
                            metavar='<status_code>')
    return parser


parsed_args = None

action_prefix = '/v1.0/tenants/<tenant_id>'
suffix = '.json'

"""Action query strings in bottle rule."""
networks_path = "/networks"
network_path = "/networks/<network_id>"
ports_path = "/networks/<network_id>/ports"
port_path = "/networks/<network_id>/ports/<port_id>"
attachment_path = "/networks/<network_id>/ports/<port_id>/attachment"


def expected_error_check(func):
    def _func(*args, **kwargs):
        status_code = getattr(parsed_args, func.func_name, None)
        if status_code:
            logging.info('Hit expected error: %s => %d',
                         func.func_name, status_code)
            abort(status_code, "Expected error for testing")
        else:
            result = func(*args, **kwargs)
            logging.debug('%s => %r', func.func_name, result)
            return result
    _func.func_name = func.func_name
    return _func


# The repository which compound from requests.
# Structure.
# Tenants
# - Networks
# -- Ports
# --- Attachment
repository = {}


def get_tenant(tenant_id):
    if tenant_id not in repository:
        abort(404, "Unknown tenant")
    return repository[tenant_id]


def get_network(tenant_id, network_id):
    tenant = get_tenant(tenant_id)
    if network_id not in tenant:
        abort(404, "Unknown network")
    return (tenant, tenant[network_id])


def get_port(tenant_id, network_id, port_id):
    (tenant, network) = get_network(tenant_id, network_id)
    if port_id not in network:
        abort(404, "Unknown port")
    return (tenant, network, network[port_id])


# Networks
@get(action_prefix + networks_path + suffix)
@expected_error_check
def list_networks(tenant_id):
    tenant = get_tenant(tenant_id)
    return {'networks': [{'id': network['id']}
                         for network in tenant.values()
                         if isinstance(network, dict)]}


@post(action_prefix + networks_path + suffix)
@expected_error_check
def create_network(tenant_id):
    tenant = get_tenant(tenant_id)
    network = json.load(request.body)
    network['id'] = str(uuid.uuid4())
    tenant[network['id']] = network
    logging.info("An network is created %s > %s",
                 tenant_id, network['id'])
    return {'network': {'id': network['id']}}


@get(action_prefix + network_path + suffix)
@expected_error_check
def show_network_details(tenant_id, network_id):
    (_tenant, network) = get_network(tenant_id, network_id)
    return {'network': {'id': network['id'],
                        'name': network['name']}}


@delete(action_prefix + network_path + suffix)
@expected_error_check
def delete_network(tenant_id, network_id):
    (tenant, _network) = get_network(tenant_id, network_id)
    del tenant[network_id]
    logging.info("An network is deleted %s > %s",
                 tenant_id, network_id)
    return HTTPResponse(status=204)


# Ports
@get(action_prefix + ports_path + suffix)
@expected_error_check
def list_ports(tenant_id, network_id):
    (_tenant, network) = get_network(tenant_id, network_id)
    return {'ports': [{'id': port['id']}
                      for port in network.values()
                      if isinstance(port, dict)]}


@post(action_prefix + ports_path + suffix)
@expected_error_check
def create_port(tenant_id, network_id):
    (_tenant, network) = get_network(tenant_id, network_id)
    port = json.load(request.body)
    port['id'] = str(uuid.uuid4())
    network[port['id']] = port
    logging.info("A port is created %s > %s > %s",
                 tenant_id, network_id, port['id'])
    return {'port': {'id': port['id']}}


@delete(action_prefix + port_path + suffix)
@expected_error_check
def delete_port(tenant_id, network_id, port_id):
    (_tenant, network, _port) = get_port(tenant_id, network_id, port_id)
    del network[port_id]
    logging.info("A port is deleted %s > %s > %s",
                 tenant_id, network_id, port_id)
    return HTTPResponse(status=204)


# Attachments
@get(action_prefix + attachment_path + suffix)
@expected_error_check
def show_port_attachment(tenant_id, network_id, port_id):
    (_tenant, _network, port) = get_port(tenant_id, network_id, port_id)
    if 'attached' in port:
        return {'attachment': {'id': port['attached']}}
    else:
        return {'attachment': {}}


@put(action_prefix + attachment_path + suffix)
@expected_error_check
def plug_port_attachment(tenant_id, network_id, port_id):
    (_tenant, _network, port) = get_port(tenant_id, network_id, port_id)
    if 'attached' in port:
        abort(440, 'Already attached')
    port['attached'] = str(uuid.uuid4())
    logging.info("A port is plugged %s > %s > %s > %s",
                 tenant_id, network_id, port['id'], port['attached'])
    return {'attachment': {'id': port['attached']}}


@delete(action_prefix + attachment_path + suffix)
@expected_error_check
def unplug_port_attachment(tenant_id, network_id, port_id):
    (_tenant, _network, port) = get_port(tenant_id, network_id, port_id)
    if 'attached' in port:
        logging.info("A port is unplugged %s > %s > %s > %s",
                     tenant_id, network_id, port['id'], port['attached'])
        del port['attached']
    else:
        logging.warn("A port was not plugged %s > %s > %s",
                     tenant_id, network_id, port['id'])
    return HTTPResponse(status=204)


def main():
    global parsed_args

    parser = get_parser()
    parsed_args = parser.parse_args()

    logger = logging.getLogger()
    if parsed_args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if parsed_args.tenant is not None:
        for tenant_id in parsed_args.tenant:
            logging.debug("Register a tenant %s", tenant_id)
            repository[tenant_id] = {}

    import bottle
    # import werkzeug.debug
    # app = bottle.app()
    # app.catchall = False
    # myapp = werkzeug.debug.DebuggedApplication(app)
    bottle.debug(parsed_args.debug)
    # bottle.run(app=myapp, host=parsed_args.host, port=parsed_args.port)
    bottle.run(host=parsed_args.host, port=parsed_args.port)


if __name__ == '__main__':
    main()
