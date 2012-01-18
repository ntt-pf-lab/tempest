#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
echo [$pwd_place] 

#pretest glance
glance -A nova index
curl -H "X-Auth-Token:nova" -H "Content-Type:application/json"  http://127.0.0.1:8774/v1.1/1/servers/1/

curl -H "X-Auth-Token:nova" -H "Content-Type:application/json" -d@create_server.json http://127.0.0.1:8774/v1.1/1/servers

./stop_mysql.sh

#tail -f /opt/openstack/log/nova-compute.log |grep -r "(TRACE|ERROR)"

