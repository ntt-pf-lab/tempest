#!/bin/sh

NOVA_MANAGE="/opt/stack/nova/bin/nova-manage"
CIDR=10.0.0.0/16
MOD_HOST=ubuntu
CMD="network modify --network=${CIDR} --host=${MOD_HOST}"
FILE_NAME=`basename $0 .sh`.log
OUTPUT_PATH=`pwd`/

#nova-manage network modify
echo "nova-manage ${CMD}" > ${OUTPUT_PATH}${FILE_NAME}
RESULT=`${NOVA_MANAGE} ${CMD}`
echo $? >> ${OUTPUT_PATH}${FILE_NAME}
echo $RESULT >> ${OUTPUT_PATH}${FILE_NAME}

