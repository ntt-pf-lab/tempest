#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    set 'flavors keypairs servers_action servers servers2 tenant through virtual_interfaces images'
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

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]

for test_case in $@; do
    printf "#########################################\n"
    printf "# Start MT TestSet %-20s #\n" $test_case
    printf "#########################################\n"
    start_sec=`date +%s`
    nosetests -v -s ./medium/tests/test_${test_case}.py
    if [ "$?" -ne "0" ]; then
        EXIT_CODE=1
    fi
    printf "########################################################\n"
    printf "# Finished MT TestSet %-20s in %05d sec #\n" $test_case $((`date +%s` - $start_sec))
    printf "########################################################\n"
done

exit $EXIT_CODE


