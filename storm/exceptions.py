class TimeoutException(Exception):
    """Exception on timeout"""
    def __repr__(self):
        return "Request timed out"


class BuildErrorException(Exception):
    """Exception on server build"""
    def __repr__(self):
        return "Server failed into error status"


class ItemNotFoundException(Exception):
    """ Exception on not found """
    def __repr__(self):
        return "Requested resource could not be found"


class BadRequest(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)
