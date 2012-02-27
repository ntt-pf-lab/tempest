#!/usr/bin/env bash

#mysql -uroot -pnova nova -e "delete from fixed_ips;"
#mysql -uroot -pnova nova -e "delete from networks;"
#mysql -uroot -pnova nova -e "delete from virtual_interfaces;"
#mysql -uroot -pnova ovs_quantum -e "delete from networks;"
source /opt/openstack/os-inst-m2/install.conf
flags=$NOVA_ETC_DIR/nova.conf
cmd="$NOVA_HOME/bin/nova-manage --flagfile=$flags"

keystone=$KEYSTONE_HOME/bin/keystone-manage
$keystone tenant add "prjTest"
$keystone user add usrTest passwordTest
$keystone role grant Member usrTest prjTest
