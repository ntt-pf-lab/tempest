#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='token delete'
FILE_NAME=`basename $0 .sh`.log
PWD=`pwd`/

tenant_id=1
tenant_name='AAA'
user_name='test_user1'
user_password='test_password1'
role_name='test_role1'
token_string='nova'
token_expires='2015-01-05T00:00'


RESULT=`${KEYSTONE_PATH} ${CMD} ${token_string}`
echo $? > ${PWD}${FILE_NAME}
echo $RESULT >> ${DESKTOP}${FILE_NAME}
