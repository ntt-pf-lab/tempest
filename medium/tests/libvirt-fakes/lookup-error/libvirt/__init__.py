import os


VIR_CRED_AUTHNAME = object()
VIR_CRED_NOECHOPROMPT = object()
VIR_ERR_NO_DOMAIN = object()


class libvirtError(Exception):
    def get_error_code(self):
        return VIR_ERR_NO_DOMAIN


def openAuth(uri, auth, n):
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
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.abspath(__file__)))),
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
        def lookupByName(instance_name):
            raise libvirtError

    return fake
