import subprocess
import shlex
import exception
import ssh
import os
import re
import config
from random import choice
from time import sleep


class HavocManager(object):
    """Manager Base Class for Havoc actions"""

    def __init__(self, host=None, username='root', password='root', **kwargs):
        self.config = config.HavocConfig()
        self.nodes = self.config.nodes
        self.services = self.config.services
        self.env = self.config.env
        self.deploy_mode = self.env.deploy_mode
        patches = kwargs.get('patches')
        self.monkey_args = ''
        timeout = self.config.nodes.ssh_timeout
        if self.deploy_mode == 'devstack-remote':
            host = self.env.devstack_host
        if host:
            self.client = self.connect(host, username, password,
                                 timeout)
        if patches:
            self._set_monkey_patch_args(patches)

    def connect(self, host, username, password, timeout):
        """Create Connection object"""

        try:
            ssh_client = ssh.Client(host, username, password, timeout)
            return ssh_client
        except:
            raise

    def _run_cmd(self, command=None):
        """Execute remote shell command, return output if successful"""
        print command
        try:
            if self.deploy_mode == 'devstack-local':
                return subprocess.check_call(command, shell=True)

            elif self.deploy_mode in ('pkg-multi', 'devstack-remote'):
                output = self.client.exec_command(command)
                exit_code = self.client.exec_command('echo $?')
                if exit_code:
                    return output.strip()
                else:
                    return False
            else:
                return False
        except:
            raise

    def _is_service_running(self, service):
        """Checks if service is running"""

        strip_grep = '[%s]' % service[0] + service[1:]
        if self.deploy_mode == 'devstack-local':

            proc1 = subprocess.Popen(shlex.split('ps aux'),
                                 stdout=subprocess.PIPE)

            proc2 = subprocess.Popen(shlex.split('grep ' + strip_grep),
                                stdin=proc1.stdout, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

            proc3 = subprocess.Popen(shlex.split('awk \'{print $2}\''),
                                stdin=proc2.stdout, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

            proc1.stdout.close()
            proc2.stdout.close()
            out, err = proc3.communicate()
            out = out.strip()
            out = out.split()
            if out:
                return out
                #return out[1]
            return False

        elif self.deploy_mode == 'pkg-multi':
            command = 'sudo service %s status' % service
            output = self._run_cmd(command)
            if 'start/running' in output:
                return True
            elif 'stop/waiting' in output:
                return False

        elif self.deploy_mode == 'devstack-remote':
            command = 'ps aux|grep %s|awk \'{print $2}\'' % strip_grep
            out = self._run_cmd(command)
            if out:
                pid = out.split('\n')
                return pid
            return False

    def _is_process_running(self, process):
        """Checks if a process is running"""

        process_check = '[%s]' % process[0] + process[1:]
        command = 'ps aux | grep %s' % process_check
        output = self._run_cmd(command).strip('\n')
        if process in output:
            return True
        return False

    def _get_service_root(self, service):
        devstack_root = self.env.devstack_root

        if 'nova' in service:
            path = os.path.join(devstack_root, 'nova/bin', service)
        elif 'glance' in service:
            path = os.path.join(devstack_root, 'glance/bin', service)
        else:
            path = os.path.join(devstack_root, service, 'bin', service)

        return path

    def _set_monkey_patch_args(self, patches):
        self.monkey_args = ' --monkey_patch=true'
        self.monkey_args += ' --monkey_patch_modules=%s' % ','.join([
                       module + ':' + patch
                       for module, patch in patches
        ])

    def service_action(self, service, action, config_file=None):
        """Perform the requested action on a service on remote host"""

        run_status = self._is_service_running(service)
	if config_file and 'nova' in service:
            config_label = '--flagfile'
        else:
            config_label = '--config_file'

        # Configure call to action for a local devstack setup
        if self.deploy_mode in ('devstack-local', 'devstack-remote'):
            self.service_root = self._get_service_root(service)
            if config_file:
                config_file = os.path.join(self.service_root, config_file)

            if action == 'start':
                if run_status:
                    return

                elif config_file:
                    config_file = os.path.join(self.env.devstack_root,
                                               config_file)

                    command = '%s %s=%s %s &' % (
                                                self.service_root, config_label,
                                                config_file,
                                                self.monkey_args)
                    if service == 'nova-compute':
                        command = 'sg libvirtd %s --flagfile=%s %s &' % (
                                        self.service_root, config_file,
                                        self.monkey_args)

                else:
                    if service == 'nova-compute':
                        command = 'sg libvirtd %s &' % self.service_root
                    else:
                        command = '%s &' % self.service_root
                self._run_cmd(command=command)

            elif action == 'stop':
                if not run_status:
                    return

                else:
                    for pid in run_status:
                        command = 'sudo kill -9 %s' % pid
                        self._run_cmd(command=command)

        # Configure call to action for a multi-node remote setup
        elif self.deploy_mode == 'pkg-multi':
            if action == 'start':
                if run_status:
                    return

            elif action in ('stop', 'restart', 'reload', 'force-reload'):
                if not run_status:
                    return

            elif action == 'status':
                    return run_status

            command = 'service %s %s' % (service, action)
            return self._run_cmd(command)

        # Configure call to action for a remote devstack setup
        elif self.deploy_mode == 'devstack-remote':
            pass

    def process_action(self,process, action):
        if action == 'killall' and self._is_process_running(process):
            command = 'killall %s' % process
            self._run_cmd(command)
            return not self._is_process_running(process)

        elif action == 'verify':
            return self._is_process_running(process)

        else:
            raise exception.HavocException


class ControllerHavoc(HavocManager):
    """Class that performs Havoc actions on Controller Node"""

    def __init__(self, host=None, username='root', password='root',
                    config_file=None):
        super(ControllerHavoc, self).__init__(host, username, password)
        self.api_service = 'nova-api'
        self.scheduler_service = 'nova-scheduler'
        self.rabbit_service = 'rabbitmq-server'
        self.mysql_service = 'mysql'
        self.config_file = config_file

    def start_nova_api(self):
        return self.service_action(self.api_service, 'start',
                                    self.config_file)

    def stop_nova_api(self):
        return self.service_action(self.api_service, 'stop')

    def restart_nova_api(self):
        return self.service_action(self.api_service, 'restart',
                                    self.config_file)

    def stop_nova_scheduler(self):
        return self.service_action(self.scheduler_service, 'stop')

    def start_nova_scheduler(self):
        return self.service_action(self.scheduler_service,
                                    'start')

    def restart_nova_scheduler(self):
        return self.service_action(self.scheduler_service,
                                    'restart')

    def stop_rabbitmq(self):
        return self.service_action(self.rabbit_service, 'stop')

    def start_rabbitmq(self):
        return self.service_action(self.rabbit_service, 'start')

    def restart_rabbitmq(self):
        return self.service_action(self.rabbit_service, 'restart')

    def stop_mysql(self):
        return self.service_action(self.mysql_service, 'stop')

    def start_mysql(self):
        return self.service_action(self.mysql_service, 'start')

    def restart_mysql(self):
        return self.service_action(self.mysql_service, 'restart')


class NetworkHavoc(HavocManager):
    """Class that performs Network node specific Havoc actions"""

    def __init__(self, host=None, username='root', password='root',
                    config_file=None):
        super(NetworkHavoc, self).__init__(host, username, password)
        self.network_service = 'nova-network'
        self.config_file = config_file

    def stop_nova_network(self):
        return self.service_action(self.network_service, 'stop')

    def start_nova_network(self):
        return self.service_action(self.network_service, 'start',
                                    self.config_file)

    def restart_nova_network(self):
        return self.service_action(self.network_service,
                                  'restart', self.config_file)

    def kill_dnsmasq(self):
        return self.process_action('dnsmasq', 'killall')

    def start_dnsmasq(self):
        """Restarting nova-network would restart dnsmasq process"""

        self.service_action(self.network_service, 'restart')
        sleep(1)
        return self.process_action('dnsmasq', 'verify')


class ComputeHavoc(HavocManager):
    """Class that performs Compute node specific Havoc actions"""

    def __init__(self, host=None, username='root', password='root',
                    config_file=None, **kwargs):
        super(ComputeHavoc, self).__init__(host, username, password, **kwargs)
        self.compute_service = 'nova-compute'
        self.terminated_instances = []
        self.config_file = config_file

    def _get_instances(self, status):
        """Uses kvm virsh to get a list of running or shutoff instances"""
        command = 'virsh list --all'
        instances = []
        output = self._run_cmd(command)
        dom_list = output.split('\n')
        for item in dom_list:
            if status in item:
                match = re.findall(r'instance-\d+', item)
                instances.extend(match)
        return instances

    def stop_nova_compute(self):
        return self.service_action(self.compute_service, 'stop')

    def start_nova_compute(self):
        return self.service_action(self.compute_service, 'start',
                                    self.config_file)

    def restart_nova_compute(self):
        return self.service_action(self.compute_service, 'restart',
                                self.config_file)

    def stop_libvirt(self):
        return self.service_action('libvirt-bin', 'stop')

    def start_libvirt(self):
        return self.service_action('libvirt-bin', 'start')

    def restart_libvirt(self):
        return self.service_action('libvirt-bin', 'restart')

    def get_running_instances(self):
        return self._get_instances('running')

    def get_stopped_instances(self):
        return self._get_instances('shut off')

    def terminate_instances(self, random=False, count=0):
        """Terminates instances randomly based on parameters passed"""

        instances = self.get_running_instances()
        if not instances:
            raise exception.HavocException

        if count and not random:
            if len(instances) < count:
                raise exception.HavocException
            else:
                for instance in instances[0:count]:
                    command = 'virsh destroy %s' % instance
                    self._run_cmd(command)
        elif random:
            if count and len(instances) >= count:
                for i in range(count):
                    command = 'virsh destroy %s' % choice(instances)
                    self._run_cmd(command)
            else:
                command = 'virsh destroy %s' % choice(instances)
                self._run_cmd(command)
        else:
            command = 'virsh destroy %s' % instances[0]
            self._run_cmd(command)

        self.terminated_instances = self.get_stopped_instances()

    def restart_instances(self):
        if not self.terminated_instances:
            raise exception.HavocException

        for instance in self.terminated_instances:
            command = 'virsh start %s' % instance
            self._run_cmd(command)


class GlanceHavoc(HavocManager):
    def __init__(self, host=None, username='root', password='root',
                        api_config_file=None, registry_config_file=None):
        super(GlanceHavoc, self).__init__(host, username, password)
        self.api_service = 'glance-api'
        self.registry_service = 'glance-registry'
        self.api_config_file = api_config_file
        self.registry_config_file = registry_config_file

    def start_glance_api(self):
        return self.service_action(self.api_service, 'start',
                                    self.api_config_file)

    def restart_glance_api(self):
        return self.service_action(self.api_service, 'restart',
                                    self.api_config_file)

    def stop_glance_api(self):
        return self.service_action(self.api_service, 'stop')

    def start_glance_registry(self):
        return self.service_action(self.registry_service, 'start',
                                    self.registry_config_file)

    def restart_glance_registry(self):
        return self.service_action(self.registry_service,
                                'restart', self.registry_config_file)

    def stop_glance_registry(self):
        return self.service_action(self.registry_service, 'stop')


class KeystoneHavoc(HavocManager):
    def __init__(self, host=None, username='root', password='root',
                    config_file=None):
        super(KeystoneHavoc, self).__init__(host, username, password)
        self.keystone_service = 'keystone'
        self.config_file = config_file

    def start_keystone(self):
        return self.service_action(self.keystone_service, 'start',
                                    self.config_file)

    def restart_keystone(self):
        return self.service_action(self.keystone_service,
                                'restart', self.config_file)

    def stop_keystone(self):
        return self.service_action(self.keystone_service, 'stop')


class QuantumHavoc(HavocManager):
    def __init__(self, host=None, username='root', password='root',
                    config_file=None, agent_config_file=None, **kwargs):
        super(QuantumHavoc, self).__init__(host, username, password, **kwargs)
        self.quantum_service = 'quantum'
        self.quantum_plugin = "quantum/plugins/openvswitch/agent/" \
                                "ovs_quantum_agent.py -v"
        self.config_file = config_file
        self.agent_config_file = agent_config_file
        self.fake_quantum_service = kwargs.get('fake_quantum_path')
        self.fake_args = kwargs.get('fake_quantum_args')

    def start_quantum(self):
        return self.service_action(self.quantum_service, 'start',
                                    self.config_file)

    def stop_quantum(self):
        return self.service_action(self.quantum_service, 'stop')

    def start_quantum_plugin(self):
        return self.service_action(self.quantum_plugin_service, 'start')

    def stop_quantum_plugin(self):
        return self.service_action(self.quantum_plugin_service, 'stop')

    def start_fake_quantum(self):
        return self.service_action(self.fake_quantum_service, 'start',
                self.fake_args)

    def stop_fake_quantum(self):
        return self.service_action(self.fake_quantum_service, 'stop')

class PowerHavoc(HavocManager):
    """Class that performs Power Management Havoc actions"""

    def __init__(self, host, username='root', password='root'):
        super(PowerHavoc, self).__init__()
        self.ipmi_host = host
        self.ipmi_user = username
        self.ipmi_password = password
        self.power_cmd = None

    def power_on(self):
        power_cmd = 'power on'
        power_on_msg = 'Chassis Power Control: Up/On'
        self.ipmi_cmd = 'ipmitool -I lan -H %s -U %s -P %s %s' % (
                                                           self.ipmi_host,
                                                           self.ipmi_user,
                                                           self.ipmi_password,
                                                           power_cmd)
        _PIPE = subprocess.PIPE
        self.ipmi_cmd_list = self.ipmi_cmd.split(" ")
        obj = subprocess.Popen(self.ipmi_cmd_list,
                               stdin=_PIPE,
                               stdout=_PIPE,
                               stderr=_PIPE,
                               )
        result = obj.communicate()
        return_status = result[0].strip()
        if power_on_msg in return_status:
            return True
        return False

    def power_off(self):
        power_cmd = 'power off'
        power_off_msg = 'Chassis Power Control: Down/Off'
        self.ipmi_cmd = 'ipmitool -I lan -H %s -U %s -P %s %s' % (
                                                           self.ipmi_host,
                                                           self.ipmi_user,
                                                           self.ipmi_password,
                                                           power_cmd)
        _PIPE = subprocess.PIPE
        self.ipmi_cmd_list = self.ipmi_cmd.split(" ")
        obj = subprocess.Popen(self.ipmi_cmd_list,
                               stdin=_PIPE,
                               stdout=_PIPE,
                               stderr=_PIPE,
                               )
        result = obj.communicate()
        return_status = result[0].strip()
        if power_off_msg in return_status:
            return True
        return False

    def is_power_on(self):
        power_cmd = 'power status'
        power_on_status_msg = 'Chassis Power is on'
        self.ipmi_cmd = 'ipmitool -I lan -H %s -U %s -P %s %s' % (
                                                           self.ipmi_host,
                                                           self.ipmi_user,
                                                           self.ipmi_password,
                                                           power_cmd)
        _PIPE = subprocess.PIPE
        self.ipmi_cmd_list = self.ipmi_cmd.split(" ")
        obj = subprocess.Popen(self.ipmi_cmd_list,
                               stdin=_PIPE,
                               stdout=_PIPE,
                               stderr=_PIPE,
                               )
        result = obj.communicate()
        return_status = result[0].strip()
        if power_on_status_msg in return_status:
            return True
        return False
