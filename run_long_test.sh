#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage input test thread count"
    exit
fi
users=$1
echo "test use $1 thread"

started=`ps -ef|grep nose|grep "large/tests/test_long_term.py"|grep -v grep |wc -l`
if [ $started -lt 0 ];then
  echo "long term test is running, stop it and try again"
  exit
fi

logd="log"
logf="TEST`date +%Y%m%d_%H%M`"
echo $logf
if [ ! -d $logd ];then
  mkdir $logd
fi
mkdir $logd/$logf

curd=`pwd`

cd /var/tmp/perf/monitor
 ./resourceMonitor.sh 30 259200 $logf $users &
../script/tail.sh &
cd $curd

######################### below is just for osf server
is_osf=`hostname |grep osf|wc -l`
if [ $is_osf -le 0 ]; then
  exit
fi

echo 0 > ./endtest.flag

i=1
while [ $i -le $users ]
do
  echo $i > ./test_thread.flag
  nosetests -s -v large/tests/test_long_term.py > ./$logd/$logf/test_thread$i.log 2>&1 &
  echo "thread $i invoked"
  i=`expr $i + 1`
  sleep 5
done
