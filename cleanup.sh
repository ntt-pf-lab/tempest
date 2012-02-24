# destroy all instance
mysql -uroot -pmysql -e 'drop database nova; create database nova'
/opt/openstack/nova/bin/nova-manage --flagfile=/opt/openstack/nova/etc/nova.conf db sync
mysql -uroot -pmysql ovs_quantum -e 'delete from ports;'
mysql -uroot -pmysql ovs_quantum -e 'delete from networks;'
cd ~/kirin/os-inst-m2
mysql -uroot -pmysql -e 'drop database keystone; create database keystone'
./init-data/init-regist-keystone.sh
cd ~/tempest

