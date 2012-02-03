import os
import re
import subprocess
import time


import storm.config
import stackmonkey.manager as ssh_manager
from nova import log


from medium.tests.processes import (
        GlanceRegistryProcess, GlanceApiProcess,
        KeystoneProcess,
        NovaApiProcess, NovaComputeProcess,
        QuantumProcess, QuantumPluginOvsAgentProcess,
        NovaNetworkProcess, NovaSchedulerProcess,
        FakeQuantumProcess)

log.setup()
config = storm.config.StormConfig('etc/large.conf')


keystone = KeystoneProcess(
                    config.keystone.directory,
                    config.keystone.config,
                    config.keystone.host,
                    config.keystone.port)


glance_reg = GlanceRegistryProcess(
                    config.glance.directory,
                    config.glance.registry_config)


glance_api = GlanceApiProcess(
                    config.glance.directory,
                    config.glance.api_config,
                    config.glance.host,
                    config.glance.port)


nova_api = NovaApiProcess(
                    config.nova.directory,
                    config.nova.host,
                    config.nova.port)


nova_compute = NovaComputeProcess(config.nova.directory,
#                                     patches=patches,
#                                     env=env,
                    config_file=config.nova.directory + 'etc/nova.conf')


nova_network = NovaNetworkProcess(
                    config.nova.directory)


quantum = QuantumProcess(
                         config.quantum.directory,
                         config.quantum.config)


quantum_agent = QuantumPluginOvsAgentProcess(
                                             config.quantum.directory,
                                             config.quantum.agent_config)
    
nova_scheduler = NovaSchedulerProcess(
                    config.nova.directory)


havoc = ssh_manager.HavocManager()


ssh_con = havoc.connect(havoc.config.nodes.api.ip,
                                          havoc.config.nodes.api.user,
                                          havoc.config.nodes.api.password,
                                          havoc.config.nodes.ssh_timeout)


ctl_havoc = ssh_manager.ControllerHavoc(havoc.config.nodes.api.ip,
                                          havoc.config.nodes.api.user,
                                          havoc.config.nodes.api.password,
                                          havoc.config.nodes.ssh_timeout)


ctl_ssh_con = ctl_havoc.connect(ctl_havoc.config.nodes.api.ip,
                                          ctl_havoc.config.nodes.api.user,
                                          ctl_havoc.config.nodes.api.password,
                                          ctl_havoc.config.nodes.ssh_timeout)

ctl_havoc_pkg = ssh_manager.ControllerHavoc(havoc.config.nodes.api.ip,
                                          havoc.config.nodes.api.user,
                                          havoc.config.nodes.api.password,
                                          havoc.config.nodes.ssh_timeout)
ctl_havoc_pkg.deploy_mode = 'pkg-multi'

ctl_ssh_con_pkg = ctl_havoc_pkg.connect(ctl_havoc_pkg.config.nodes.api.ip,
                                          ctl_havoc_pkg.config.nodes.api.user,
                                          ctl_havoc_pkg.config.nodes.api.password,
                                          ctl_havoc_pkg.config.nodes.ssh_timeout)


glance_havoc = ssh_manager.GlanceHavoc(
                    host=havoc.config.nodes.glance.ip,
                    username=havoc.config.nodes.glance.user,
                    password=havoc.config.nodes.glance.password,
                    api_config_file=os.path.join(config.glance.directory,
                                                 config.glance.api_config),
                    registry_config_file=os.path.join(config.glance.directory,
                                                config.glance.registry_config))


glance_ssh_con = glance_havoc.connect(
                                    havoc.config.nodes.glance.ip,
                                    havoc.config.nodes.glance.user,
                                    havoc.config.nodes.glance.password,
                                    glance_havoc.config.nodes.ssh_timeout)


compute_havoc = ssh_manager.ComputeHavoc(
                        host=havoc.config.nodes.compute.ip,
                        username=havoc.config.nodes.compute.user,
                        password=havoc.config.nodes.compute.password,
                        config_file=os.path.join(config.nova.directory,
                                                 'etc/nova.conf')
                        )


compute_ssh_con = compute_havoc.connect(
                                havoc.config.nodes.compute.ip,
                                havoc.config.nodes.compute.user,
                                havoc.config.nodes.compute.password,
                                compute_havoc.config.nodes.ssh_timeout)


def start_nova_api():
    ctl_havoc.start_nova_api()


def stop_nova_api():
    ctl_havoc.stop_nova_api()


def start_mysql():
    ctl_havoc_pkg.start_mysql()


def stop_mysql():
    ctl_havoc_pkg.stop_mysql()


def start_glance_api():
    glance_havoc.start_glance_api()
    time.sleep(0.1)


def stop_glance_api():
    glance_havoc.stop_glance_api()
    time.sleep(0.1)


def start_nova_compute():
    compute_havoc.start_nova_compute()


def start_nova_compute_with_patch(fake_path, patches):
    compute_havoc.python_path = _get_fake_path(fake_path)
    #[('nova.virt.libvirt.connection', 'fake_libvirt.libvirt_con_get_info_patch')]
    compute_havoc._set_monkey_patch_args(patches)
    compute_havoc.start_nova_compute()


def stop_nova_compute():
    compute_havoc.stop_nova_compute()


def _get_fake_path(name):
    return os.path.join(
            os.path.dirname(__file__),
            '../../medium/tests/fakes',
            name)


def get_nova_path(self, name):
    p = os.path.dirname(__file__)
    p = p.split(os.path.sep)[0:-2]
    return os.path.join(os.path.sep.join(p), name)

