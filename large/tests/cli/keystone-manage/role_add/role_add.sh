#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='role add'
FILE_NAME=`basename $0 .sh`.log
PWD=`pwd`/

tenant_id=1
tenant_name='AAA'
user_name='test_user1'
user_password='test_password1'
role_name='test_role1'
token_string='test_token_string1'
token_expires='2015-02-05T00:00'


RESULT=`${KEYSTONE_PATH} ${CMD} ${role_name}`
echo $? > ${PWD}${FILE_NAME}
echo $RESULT >> ${PWD}${FILE_NAME}
