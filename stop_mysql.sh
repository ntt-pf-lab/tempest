#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
echo [$pwd_place] 

fname="flag_stop_mysql"
while [ 1 ]
do
    echo "wait flag file to stop mysql......"
    if [ -f $fname ];then
        echo "stop mysql service at $exec_date"
        sudo service mysql stop
        rm -f $fname
        exit 0
    fi
    sleep 1
done

