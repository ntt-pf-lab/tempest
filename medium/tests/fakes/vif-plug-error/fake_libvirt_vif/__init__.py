from nova import exception


def fake_plug(self, instance, network, mapping):
    raise exception.ProcessExecutionError


def vif_patch(name, fn):
    if name == 'nova.virt.libvirt.vif.LibvirtOpenVswitchDriver.plug':
        return fake_plug
    else:
        return fn
