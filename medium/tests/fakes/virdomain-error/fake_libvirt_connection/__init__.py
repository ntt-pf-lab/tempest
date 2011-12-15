from nova import exception


def fake_get_info(self, instance_name):
    raise exception.InstanceNotFound(instance_name)


def patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection.get_info':
        return fake_get_info
    else:
        return fn

