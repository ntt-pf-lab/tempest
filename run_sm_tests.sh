exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]

nosetests -v -s
./medium/tests/test_opposite_system_illegal_state_create_image.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

nosetests -v -s
./medium/tests/test_opposite_system_illegal_state_create_server.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

nosetests -v -s
./medium/tests/test_opposite_system_illegal_state_delete_server.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

nosetests -v -s
./medium/tests/test_opposite_system_illegal_state_reboot_server.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

nosetests -v -s ./medium/tests/test_process_down.py
if [ "$?" -ne "0" ]; then
    EXIT_CODE=1
fi

exit $EXIT_CODE
