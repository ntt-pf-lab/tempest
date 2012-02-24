#!/bin/sh

NOVA_MANAGE="/opt/stack/nova/bin/nova-manage"
CMD='network delete --uuid'
FILE_NAME=`basename $0 .sh`.log
OUTPUT_PATH=`pwd`/
UUID=1234567890

#nova-manage network delete
echo "nova-manage network delete" >> ${OUTPUT_PATH}${FILE_NAME}
RESULT=`${NOVA_MANAGE} ${CMD} ${UUID}`
echo $? >> ${OUTPUT_PATH}${FILE_NAME}
echo $RESULT >> ${OUTPUT_PATH}${FILE_NAME}

