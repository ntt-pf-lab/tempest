import subprocess


def fake_plug(self, instance, network, mapping):
    raise subprocess.ProcessExecutionError


def vif_patch(name, fn):
    if name == 'vif.LibvirtOpenVswitchDriver.plug':
        return fake_plug
    else:
        return fn
