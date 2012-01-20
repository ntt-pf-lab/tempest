#!/usr/bin/env bash

nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_detail_when_three_servers_created
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_status_active 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_status_build_when_server_is_active 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_status_build_when_server_is_build 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_status_is_invalid 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_string_to_flavor 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_string_to_image 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_specify_string_to_limits 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_status_is_deleted 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_when_no_server_created 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_when_one_server_created 
nosetests -v -s medium.tests.test_servers:ServersTest.test_list_servers_when_three_servers_created 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_empty_name 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_not_exists_id 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_same_name 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_specify_other_tenant_server 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_specify_overlimits_to_name 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_specify_uuid 
nosetests -v -s medium.tests.test_servers:ServersTest.test_update_server_when_create_image 

# execute this case after delete glance-api.cong and glance-registry.conf 's debuglogger setting
nosetests -v -s medium.tests.test_servers_action:CreateImageFatTest.test_create_image_fat_snapshot

