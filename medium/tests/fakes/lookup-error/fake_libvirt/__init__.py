import os
import libvirt
import traceback

try:
    import libvirtmod
except ImportError, lib_e:
    try:
        import cygvirtmod as libvirtmod
    except ImportError, cyg_e:
        if str(cyg_e).count("No module named"):
            raise lib_e


class fake(object):
    @staticmethod
    def defineXML(xml):
        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass
        return fake_domain

    @staticmethod
    def listDomainsID():
        return []

    @staticmethod
    def getCapabilities():
        return file(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'capabilities.xml')).read()

    @staticmethod
    def getType():
        return 'qemu'

    @staticmethod
    def getVersion():
        return '12003'

    @staticmethod
    def nwfilterDefineXML(xml):
        pass

    @staticmethod
    def nwfilterLookupByName(instance_filter_name):
        pass

    @staticmethod
    def lookupByName(instance_name):
        raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)


def openAuth(uri, auth, n):
    return fake


def libvirt_patch(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth
    else:
        return fn


class fake_vir_error(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('destroy', 'reboot', 'snapshot',
                             'reboot_instance'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}
        return fake_domain


def openAuth_vir_error(uri, auth, n):
    return fake_vir_error


def libvirt_patch_vir_error(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_vir_error
    else:
        return fn


class fake_vir_error_rd(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('destroy'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}

            @staticmethod
            def XMLDesc(flag):
                return ''

        return fake_domain


def openAuth_vir_error_rd(uri, auth, n):
    return fake_vir_error_rd


def libvirt_patch_vir_error_rd(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_vir_error_rd
    else:
        return fn


class fake_vir_error_rd_conf(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('_wait_for_reboot'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_ERROR)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}

            @staticmethod
            def XMLDesc(flag):
                return ''

        return fake_domain


def openAuth_vir_error_rd_conf(uri, auth, n):
    return fake_vir_error_rd_conf


def libvirt_patch_vir_error_rd_conf(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_vir_error_rd_conf
    else:
        return fn


class fake_no_domain(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('destroy', 'reboot', 'snapshot',
                             'reboot_instance'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_NO_DOMAIN)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}
        return fake_domain


def openAuth_no_domain(uri, auth, n):
    return fake_no_domain


def libvirt_patch_no_domain(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_no_domain
    else:
        return fn


class fake_no_domain_rd(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('destroy'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_NO_DOMAIN)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}

            @staticmethod
            def XMLDesc(flag):
                return ''

        return fake_domain


def openAuth_no_domain_rd(uri, auth, n):
    return fake_no_domain_rd


def libvirt_patch_no_domain_rd(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_no_domain_rd
    else:
        return fn


class fake_no_domain_rd_conf(fake):
    @staticmethod
    def lookupByName(instance_name):
        flag_in_target = False
        try:
            raise Exception
        except Exception, e:
            lst = traceback.extract_stack()
            for mi in lst:
                if mi[2] in ('_wait_for_reboot'):
                    flag_in_target = True
        if flag_in_target:
            raise libvirt.libvirtError(libvirt.VIR_ERR_NO_DOMAIN)

        class fake_domain(object):
            @staticmethod
            def createWithFlags(flag):
                pass

            @staticmethod
            def info():
                return {'state': 1,
                        'max_mem': '2048',
                        'mem': '1024',
                        'num_cpu': '2',
                        'cpu_time': '1'}

            @staticmethod
            def XMLDesc(flag):
                return ''

        return fake_domain


def openAuth_no_domain_rd_conf(uri, auth, n):
    return fake_no_domain_rd_conf


def libvirt_patch_no_domain_rd_conf(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_no_domain_rd_conf
    else:
        return fn


class fake_no_domain_nopass(fake):
    @staticmethod
    def lookupByName(instance_name):
        raise libvirt.libvirtError(libvirt.VIR_ERR_NO_DOMAIN)


def openAuth_no_domain_nopass(uri, auth, n):
    return fake_no_domain_nopass


def libvirt_patch_no_domain_nopass(name, fn):
    if name == 'libvirt.openAuth':
        return openAuth_no_domain_nopass
    else:
        return fn


def fake_get_info_OK(self, instance_name):
    return {'state': 1,
                'max_mem': '2048',
                'mem': '1024',
                'num_cpu': '2',
                'cpu_time': '1'}


def libvirt_con_get_info_patch(name, fn):
    if name == 'nova.virt.libvirt.connection.LibvirtConnection.get_info':
        return fake_get_info_OK
    else:
        return fn
