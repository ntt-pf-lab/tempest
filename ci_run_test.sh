#!/usr/bin/env bash

exec_date=`date '+%Y%m%d%H%M'`
pwd_place=`pwd`
EXIT_CODE=0
echo [$pwd_place]

for test_case in $@; do
    printf "#########################################\n"
    printf "# Start MT TestSet %-20s #\n" $test_case
    printf "#########################################\n"
    start_sec=`date +%s`
    nosetests -v -s ./medium/tests/test_${test_case}.py
    if [ "$?" -ne "0" ]; then
        EXIT_CODE=1
    fi
    printf "########################################################\n"
    printf "# Finished MT TestSet %-20s in %05d sec #\n" $test_case $((`date +%s` - $start_sec))
    printf "########################################################\n"
done

exit $EXIT_CODE

