#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='disable'
FILE_NAME=`basename $0 .sh`.log
DESKTOP="/home/openstack/Desktop/"

tenant='tenant'
tenant_id=11
tenant_name='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
user_name='test'
user_password='test_password1'
role_name='test_role1'
token_string='test_token_string1'
token_expires='2015-02-05T00:00'


RESULT=`${KEYSTONE_PATH} ${tenant} ${CMD} ${tenant_name}`
echo $? > ${DESKTOP}${FILE_NAME}
echo $RESULT >> ${DESKTOP}${FILE_NAME}
