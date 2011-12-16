from nova import exception


def fake_unplug(self, instance, network, mapping):
    raise exception.ProcessExecutionError


def vif_patch(name, fn):
    if name == 'nova.virt.libvirt.vif.LibvirtOpenVswitchDriver.unplug':
        return fake_unplug
    else:
        return fn
