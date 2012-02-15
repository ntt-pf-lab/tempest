#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='endpoint add'
FILE_NAME=`basename $0 .sh`.log
PWD=`pwd`/

tenant_id=2
tenant_name='AAA'
user_name='test_user1'
user_password='test_password1'
role_name='test_role1'
token_string='test_token_string1'
token_expires='2015-02-05T00:00'
endpoint_id=1
endpoint_region='RegionOne'
service_name='nova'
endpoint_public_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_admin_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_internal_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_enabled=1
endpoint_is_global=1

RESULT=`${KEYSTONE_PATH} ${CMD} ${tenant_id} ${endpoint_id}`
echo $? > ${PWD}${FILE_NAME}
echo $RESULT >> ${PWD}${FILE_NAME}
