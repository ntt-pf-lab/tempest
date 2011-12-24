#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]
nosetests -s ./medium/tests/test_flavors.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_images.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_keypairs.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_servers_action.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_servers.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_tenant.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
nosetests -s ./medium/tests/test_through.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi
osetests -s ./medium/tests/test_virtual_interfaces.py
if [ $? != 0 ]; then
    EXIT_CODE=1
fi

exit $EXIT_CODE


