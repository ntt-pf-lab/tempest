#!/bin/sh

NOVA_MANAGE="/opt/stack/nova/bin/nova-manage"
CMD='network delete --uuid='
FILE_NAME=`basename $0 .sh`.log
OUTPUT_PATH=`pwd`/

#create network
${NOVA_MANAGE} network create --label=private_9-1 --project_id=1 --fixed_range_v4=10.0.9.0/24 --bridge_interface=br-int --num_networks=1 --network_size=32

#get uuid
UUID=`mysql nova -u root -pnova -h ubuntu -N -e "select uuid from networks where cidr='10.0.9.0/24'"`

#get networks
CIDR=`mysql nova -u root -pnova -h ubuntu -N -e "select cidr from networks"`

echo "Before Delete" > ${OUTPUT_PATH}${FILE_NAME}
echo $CIDR >> ${OUTPUT_PATH}${FILE_NAME}

#nova-manage network delete
echo "nova-manage ${CMD}${UUID}" >> ${OUTPUT_PATH}${FILE_NAME}
RESULT=`${NOVA_MANAGE} ${CMD}${UUID}`
echo $? >> ${OUTPUT_PATH}${FILE_NAME}
echo $RESULT >> ${OUTPUT_PATH}${FILE_NAME}

#get networks
CIDR=`mysql nova -u root -pnova -h ubuntu -N -e "select cidr from networks"`
echo "After Delete" >> ${OUTPUT_PATH}${FILE_NAME}
echo $CIDR >> ${OUTPUT_PATH}${FILE_NAME}

