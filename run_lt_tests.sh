#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]
nosetests -s ./medium/tests/test_flavors.py ./medium/tests/test_images.py ./medium/tests/test_keypairs.py ./medium/tests/test_servers_action.py ./medium/tests/test_servers.py ./medium/tests/test_tenant.py ./medium/tests/test_through.py ./medium/tests/test_virtual_interfaces.py

if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

exit $EXIT_CODE


