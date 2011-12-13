from nova import exception


def fake_unfilter_instance(self, instance, network_info):
    raise exception.ProcessExecutionError


def unfilter_patch(name, fn):
    if name in(
        'nova.virt.libvirt.firewall.IptablesFirewallDriver.unfilter_instance',
        'nova.virt.libvirt.firewall.NWFilterFirewall.unfilter_instance'):
        return fake_unfilter_instance
    else:
        return fn
