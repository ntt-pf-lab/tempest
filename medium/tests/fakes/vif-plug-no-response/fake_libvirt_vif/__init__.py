import time
import logging


def fake_plug(self, instance, network, mapping):
    # XXX Should notify something via notification framework.
    logging.error("Start SLEEP" + " z" * 10)
    time.sleep(60 * 60 * 100)  # 100 hours


def vif_patch(name, fn):
    if name == 'nova.virt.libvirt.vif.LibvirtOpenVswitchDriver.plug':
        return fake_plug
    else:
        return fn
