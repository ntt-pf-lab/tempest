#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    set 'flavors keypairs reboot_server create_image create_server delete_update_server list_server tenant through virtual_interfaces images'
#commeted out: set 'servers_action servers servers2'
fi

# allocate networks.
#mysql -uroot -pnova nova -e "delete from fixed_ips;"
#mysql -uroot -pnova nova -e "delete from networks;"
#mysql -uroot -pnova nova -e "delete from virtual_interfaces;"
#mysql -uroot -pnova ovs_quantum -e "delete from networks;"

cmd=/opt/openstack/nova/bin/nova-manage
#cmd=/opt/stack/nova/bin/nova-manage
$cmd network create --label=private_1-1 --project_id=1 --fixed_range_v4=10.0.0.0/24 --bridge_interface=br-int --num_networks= --network_size=32
$cmd network create --label=private_1-2 --project_id=1 --fixed_range_v4=10.0.1.0/24 --bridge_interface=br-int --num_networks= --network_size=32
$cmd network create --label=private_1-3 --project_id=1 --fixed_range_v4=10.0.2.0/24 --bridge_interface=br-int --num_networks= --network_size=32
$cmd network create --label=private_2-1 --project_id=2 --fixed_range_v4=10.0.3.0/24 --bridge_interface=br-int --num_networks= --network_size=32

keystone=/opt/openstack/keystone/bin/keystone-manage
$keystone tenant add "prjTest"
$keystone user add usrTest passwordTest
$keystone role grant Member usrTest prjTest
