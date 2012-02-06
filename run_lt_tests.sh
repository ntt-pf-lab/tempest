#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    set 'flavors keypairs reboot_server create_image create_server delete_update_server list_server tenant through virtual_interfaces images'
#commeted out: set 'servers_action servers servers2'
fi
./ci_setup.sh
./ci_run_test.sh

