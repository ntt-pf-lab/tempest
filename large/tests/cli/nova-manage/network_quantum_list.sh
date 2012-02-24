#!/bin/sh

NOVA_MANAGE="/opt/stack/nova/bin/nova-manage"
CMD="network quantum_list"
FILE_NAME=`basename $0 .sh`.log
OUTPUT_PATH=`pwd`/

#nova-manage network quantum_list
${NOVA_MANAGE} ${CMD} >> ${OUTPUT_PATH}${FILE_NAME}
echo $? >> ${OUTPUT_PATH}${FILE_NAME}

