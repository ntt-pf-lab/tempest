from nose.plugins.attrib import attr
from tempest import exceptions
from tempest import manager
from tempest.common.utils.data_utils import rand_name
from tempest.tests.compute.base import BaseComputeTest


class VirtualInterfacesTest(BaseComputeTest):

    @classmethod
    def setUpClass(cls):
        cls.wb_manager = manager.WhiteBoxManager()
        cls.wb_manager.connect_db()
        cls.client = cls.servers_client
        # Set the tenant by calling keystone_auth()
        cls.client.get_auth()
        cls.network_client = cls.os.network_client

    def tearDown(cls):
        for server in cls.servers:
            try:
                cls.client.delete_server(server['id'])
            except exceptions.NotFound:
                continue

    @attr(type='whitebox')
    def test_list_virtual_interfaces_when_network_is_deleted(self):
        """List virtual interfaces of server when network is deleted"""

        # Create a test network
        label = 'wb_test'
        cidr = '10.0.10.0/24'
        params = '--label=%s --fixed_range_v4=%s --project_id=%s' % (
                                                                   label, cidr,
                                                         self.client.tenant_id)
        self.wb_manager.nova_manage('network', 'create', params)

        sql = 'SELECT id, uuid from networks WHERE label=%s'
        result = self.wb_manager.execute_query(sql, label, num_records='one')

        # Create server in the network
        fixed_ip = '10.0.10.100'
        network_id = result['id']
        uuid = result['uuid']
        networks = [{'uuid':uuid, 'fixed_ip':fixed_ip}]
        resp, srv = self.client.create_server('test-vm-001', self.image_ref,
                                              self.flavor_ref,
                                              networks=networks)
        # Delete the network
        sql = 'UPDATE networks SET deleted=1 WHERE uuid=%s'
        self.wb_manager.execute_query(sql, uuid)
        try:
            resp, vif = self.client.list_server_virtual_interfaces(srv['id'])
            self.assertEqual('200', resp['status'])
            self.assertEqual([], vif['virtual_interfaces'])
        except:
            self.fail("Failed to list virtual interfaces for server when it's"
                      " network is deleted")
        finally:
            self.client.delete_server(srv['id'])
            # Clean up test network in Nova
            sql1 = 'DELETE from networks WHERE uuid=%s'
            sql2 = 'DELETE from fixed_ips WHERE id=%s'
            self.wb_manager.execute_query(sql1, uuid)
            self.wb_manager.execute_query(sql2, network_id)

            # Clean up test network in Quantum
            self.network_client.delete_network(uuid)

    @attr(type='whitebox')
    def test_list_virtual_interfaces_server_in_multiple_networks(self):
        """List virtual interfaces for server present in multiple networks"""

        label = 'wb_test'
        networks = []
        network_ids = []
        cidrs = ['10.0.6.0/24', '10.0.7.0/25']

        # Create three test networks
        for cidr in cidrs:
            params = '--label=%s --fixed_range_v4=%s --project_id=%s' % (
                                                                   label, cidr,
                                                         self.client.tenant_id)
            self.wb_manager.nova_manage('network', 'create', params)

            sql = 'SELECT id, uuid from networks WHERE cidr=%s'
            result = self.wb_manager.execute_query(sql, cidr,
                                                   num_records='one')
            # Create server in the network
            fixed_ip = '.'.join(cidr.split('.')[0:3]) + '.100'
            network_ids.append(result['id'])
            uuid = result['uuid']
            network = {'uuid': uuid, 'fixed_ip': fixed_ip}
            networks.append(network)

        try:
            resp, srv = self.client.create_server(rand_name('test-vm-'),
                                                  self.image_ref,
                                                  self.flavor_ref,
                                                  networks=networks)
            self.client.wait_for_server_status(srv['id'], 'ACTIVE')

            # Verify two virtual interfaces created and attached
            resp, body = self.client.list_server_virtual_interfaces(srv['id'])
            self.assertEqual('200', resp['status'])
            vifs = body['virtual_interfaces']
            self.assertTrue(len(vifs) == 2)
        except:
            self.fail("Failed to list virtual interfaces when server has "
                      "multiple network interfaces")

        finally:
            self.client.delete_server(srv['id'])
            self.client.wait_for_server_termination(srv['id'])
            resp, body = self.network_client.list_networks()

            # Delete networks from nova and quantum
            for network in networks:
                uuid = network['uuid']
                resp, body = self.network_client.list_port_details(uuid)
                ports = body['ports']
                for port in ports:
                    self.network_client.detach_port(uuid, port['id'])

                params = '--uuid=%s' % uuid
                self.wb_manager.nova_manage('network', 'delete', params)
            sql = 'DELETE from fixed_ips WHERE deleted=1'
            self.wb_manager.execute_query(sql)
