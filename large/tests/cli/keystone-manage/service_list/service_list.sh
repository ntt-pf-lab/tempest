#!/bin/sh

KEYSTONE_PATH="/opt/stack/keystone/bin/keystone-manage --config-file=/opt/stack/keystone/etc/keystone.conf"
CMD='service list'
FILE_NAME=`basename $0 .sh`.log
PWD=`pwd`/

tenant_id=1
tenant_name='AAA'
user_name='test_user1'
user_password='test_password1'
role_name='test_role1'
token_string='test_token_string1'
token_expires='2015-02-05T00:00'
endpoint_region='RegionOne'
service_name='nova'
endpoint_public_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_admin_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_internal_url='http://127.0.0.1:9696/v1.0/tenants/%tenant_id%'
endpoint_enabled=1
endpoint_is_global=1

${KEYSTONE_PATH} ${CMD} ${endpoint_region} ${service_name} ${endpoint_public_url} ${endpoint_admin_url} ${endpoint_internal_url} ${endpoint_enabled} ${endpoint_is_global} > ${PWD}${FILE_NAME}
echo $? >> ${PWD}${FILE_NAME}
