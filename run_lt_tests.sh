#!/usr/bin/env bash


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

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]
nosetests -v -s ./medium/tests/test_flavors.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_images.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_keypairs.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_servers_action.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_servers.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_tenant.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_through.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi
nosetests -v -s ./medium/tests/test_virtual_interfaces.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

exit $EXIT_CODE


