#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='role grant'
FILE_NAME=`basename $0 .sh`.log
PWD=`pwd`/

tenant_id=1
tenant_name='invisible_to_admin'
user_id=3
user_name='admin'
user_password='test_password1'
role_name='Admin'
token_string='test_token_string1'
token_expires='2015-02-05T00:00'


RESULT=`${KEYSTONE_PATH} ${CMD} ${role_name} ${user_name} ${tenant_name}`
echo $? > ${PWD}${FILE_NAME}
echo $RESULT >> ${DESKTOP}${FILE_NAME}
