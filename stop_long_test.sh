#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage input log fold name created by start"
    exit
fi
logf=$1

echo 1 > ./endtest.flag

ps -ef|grep resourceMonitor|grep -v grep|awk '{print "kill -15 ",$2}'|sh
ps -ef|grep tail|grep "follow=name"|grep log|grep -v grep|awk '{print "kill -9", $2}'|sh

curd=`pwd`
hn=`hostname`
mkdir $curd/log/${logf}/$hn

cd /var/tmp/perf/monitor/data/
#tar -czf resource.tgz ${logf}/
cp ${logf}/*  $curd/log/${logf}/$hn

cd /var/tmp/perf/
#tar -czf nova.tgz etcLog/
novalog="etcLog_$hn"
mkdir $curd/log/${logf}/$novalog
cp etcLog/* $curd/log/${logf}/$novalog

cd $curd/log/
zip -r ${logf}_${hn}.zip ${logf}/
rm -fr ${logf}/

cd $curd


