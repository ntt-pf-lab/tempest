#!/usr/bin/env bash

#mysql -uroot -pnova nova -e "delete from fixed_ips;"
#mysql -uroot -pnova nova -e "delete from networks;"
#mysql -uroot -pnova nova -e "delete from virtual_interfaces;"
#mysql -uroot -pnova ovs_quantum -e "delete from networks;"
source /opt/openstack/os-inst-m2/install.conf
flags=$NOVA_ETC_DIR/nova.conf
cmd="$NOVA_HOME/bin/nova-manage --flagfile=$flags"
$cmd network create --label=private_1-1 --project_id=1 --fixed_range_v4=10.0.0.0/24 --bridge_interface=br-int --num_networks= --network_size=32 --gateway=10.0.0.1
$cmd network create --label=private_1-2 --project_id=1 --fixed_range_v4=10.0.1.0/24 --bridge_interface=br-int --num_networks= --network_size=32 --gateway=10.0.1.1
$cmd network create --label=private_1-3 --project_id=1 --fixed_range_v4=10.0.2.0/24 --bridge_interface=br-int --num_networks= --network_size=32 --gateway=10.0.2.1
$cmd network create --label=private_2-1 --project_id=2 --fixed_range_v4=10.0.3.0/24 --bridge_interface=br-int --num_networks= --network_size=32 --gateway=10.0.3.1

keystone=$KEYSTONE_HOME/bin/keystone-manage
$keystone tenant add "prjTest"
$keystone user add usrTest passwordTest
$keystone role grant Member usrTest prjTest
