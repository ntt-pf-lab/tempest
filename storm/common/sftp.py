import socket
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko


class Client(object):

    def __init__(self, host, username, password, timeout=300):
        self.host = host
        self.username = username
        self.password = password
        self._transport = None

    def _get_connection(self):
        _transport = paramiko.Transport((self.host))
        try:
            _transport.connect(username=self.username, password=self.password)
            sftp_connection = paramiko.SFTPClient.from_transport(_transport)
        except socket.error:
            return False
        except paramiko.AuthenticationException:
            return False
        return sftp_connection

    def put(self, localpath, remotepath):
        """Transfer file to remote host."""
        sftp_connection = self._get_connection()
        if not sftp_connection:
            return False

        try:
            status = sftp_connection.put(localpath, remotepath, confirm=True)
        except:
            return False
        sftp_connection.close()
        return True

    def get(self, remotepath, localpath):
        """Fetch a file from the remote host."""
        sftp_connection = self._get_connection()
        if not sftp_connection:
            return False

        try:
            status = sftp_connection.get(remotepath, localpath)
        except:
            return False
        sftp_connection.close()
        return True
