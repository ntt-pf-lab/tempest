import threading


class RequestThread(threading.Thread):
    def __init__(self, api_method, kwargs=None):
        self._api_method = api_method
        self._response = None
        self.kwargs = kwargs
        threading.Thread.__init__(self)

    def run(self):
        """Make the API call and record the response time."""
        if self.kwargs:
            self._response = self._api_method(self.kwargs)
        else:
            self._response = self._api_method()

    def get_response(self):
        return self._response


def log_api_perf_results(filename, result_dict):
    """Log the results to the perf log file."""
    log_list = ["-" * 50,
                result_dict['api_name'],
                "WITH_DEBUGLOG\tWITHOUT_DEBUGLOG"]
    sum_t1 = 0
    sum_t2 = 0
    for (t1, t2) in result_dict['results']:
        sum_t1 += float(t1)
        sum_t2 += float(t2)
        log_list.append("%s\t\t%s" % (str(t1), str(t2)))
    test_count = len(result_dict['results'])
    avg_diff = float(sum_t1 / test_count) - float(sum_t2 / test_count)
    log_list.append("Average difference: %.6f" % avg_diff)
    log_str = "\n".join(log_list) + "\n"

    fp = open(filename, "a")
    fp.write(log_str)
    fp.close()
