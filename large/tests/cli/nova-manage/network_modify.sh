#!/bin/sh

NOVA_MANAGE="/opt/stack/nova/bin/nova-manage"
CIDR=10.0.9.0/24
MOD_HOST=ubuntu
CMD="network modify --network=${CIDR} --host=${MOD_HOST}"
FILE_NAME=`basename $0 .sh`.log
OUTPUT_PATH=`pwd`/

#create network
${NOVA_MANAGE} network create --label=private_9-1 --project_id=1 --fixed_range_v4=${CIDR} --bridge_interface=br-int --num_networks=1 --network_size=32

echo "value of host before modify" > ${OUTPUT_PATH}${FILE_NAME}
BF_HOST=`mysql nova -u root -pnova -h ubuntu -N -e "select host from networks where cidr = '${CIDR}'"`
echo $BF_HOST >> ${OUTPUT_PATH}${FILE_NAME}

#nova-manage network modify
echo "nova-manage ${CMD}" >> ${OUTPUT_PATH}${FILE_NAME}
RESULT=`${NOVA_MANAGE} ${CMD}`
echo $? >> ${OUTPUT_PATH}${FILE_NAME}
echo $RESULT >> ${OUTPUT_PATH}${FILE_NAME}

echo "value of host after modify" >> ${OUTPUT_PATH}${FILE_NAME}
AF_HOST=`mysql nova -u root -pnova -h ubuntu -N -e "select host from networks where cidr = '${CIDR}'"`
echo $AF_HOST >> ${OUTPUT_PATH}${FILE_NAME}

#nova-manage network delete
UUID=`mysql nova -u root -pnova -h ubuntu -N -e "select uuid from networks where cidr='${CIDR}'"`
echo "nova-manage network delete --uuid=${UUID}" >> ${OUTPUT_PATH}${FILE_NAME}
RESULT=`${NOVA_MANAGE} network delete --uuid=${UUID}`
echo $? >> ${OUTPUT_PATH}${FILE_NAME}
echo $RESULT >> ${OUTPUT_PATH}${FILE_NAME}

