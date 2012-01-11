class HavocException(Exception):
    """Base Havoc Exception"""

    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        if not message:
            try:
                message = self.message % kwargs

            except Exception as e:
                message = self.message

        super(HavocException, self).__init__(message)


class SSHException(HavocException):
    message = "Exception thrown during SSH operation"
