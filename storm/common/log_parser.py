import codecs
import os


class CustomLogParser(object):
    def __init__(self, filename):
        self.filename = filename
        self.data = []

    def __load_log_messages(self):
        fp = codecs.open(self.filename, "r", "utf-8")
        self.data = fp.readlines()
        fp.close()

    def fetch_request_logs(self, request_id):
        if os.path.exists(self.filename) and os.access(self.filename, os.R_OK):
            self.__load_log_messages()
            filtered_logs = []
            for line in self.data:
                if line.find(request_id) != -1:
                    filtered_logs.append(line)
            self.data = []
            return filtered_logs
        else:
            print _("Unable to read log file %s") % self.filename
            return False
