import os


VIR_CRED_AUTHNAME = object()
VIR_CRED_NOECHOPROMPT = object()


class libvirtError(Exception):
    pass


def openAuth(uri, auth, n):
    class fake(object):
        @staticmethod
        def defineXML(xml):
            raise libvirtError

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

    return fake
