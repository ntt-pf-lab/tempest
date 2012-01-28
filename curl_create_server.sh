#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
echo [$pwd_place] 

id="d02-101"
mkdir log-create-server/$id

#pretest glance
glance -A nova index
curl -H "X-Auth-Token:nova" -H "Content-Type:application/json"  http://127.0.0.1:8774/v1.1/1/servers/1/

tail -f /opt/openstack/log/nova-compute.log > log-create-server/$id/nova-compute.log &

curl -H "X-Auth-Token:nova" -H "Content-Type:application/json" -d@create_server.json http://127.0.0.1:8774/v1.1/1/servers

./stop_mysql.sh


