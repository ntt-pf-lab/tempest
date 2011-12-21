#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
echo [$pwd_place] 
nosetests -s ./medium/tests/test_flavors.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_images.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_keypairs.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_servers_action.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_servers.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_tenant.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_through.py 2>&1 |tee -a medium/tests/$exec_date.log
nosetests -s ./medium/tests/test_virtual_interfaces.py 2>&1 |tee -a medium/tests/$exec_date.log



