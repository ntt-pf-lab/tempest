import re
import threading
from datetime import datetime, timedelta
from storm.common.log_parser import CustomLogParser


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


def convert_timedelta_to_milliseconds(td):
    """convert timedelta to milliseconds"""
    ms = td.days * 86400 * 1E3 + td.seconds * 1E3 + td.microseconds / 1E3
    return ms


class LogAnalyzer:
    def __init__(self, file_name, date_regex, date_format):
        self.log_parser = CustomLogParser(file_name)
        self.date_regex = date_regex
        self.date_format = date_format

    def fetch_request_metrics(self, request_id, task_name_log_map,
                              timedelta_convertor=None):
        """Fetch the request logs and calculate metrics"""
        metrics = []

        request_logs = self.log_parser.fetch_request_logs(request_id)
        if request_logs:
            if not timedelta_convertor:
                timedelta_convertor = convert_timedelta_to_milliseconds

            mObj = re.search(self.date_regex, request_logs[0])
            if not mObj:
                return metrics
            start_time = datetime.strptime(mObj.group('date_time'),
                                           self.date_format)

            mObj = re.search(self.date_regex, request_logs[-1])
            end_time = datetime.strptime(mObj.group('date_time'),
                                         self.date_format)

            task_time = {}
            last_time = start_time
            start_index = 0
            for task, log_msg in task_name_log_map:
                found = False
                for index in range(start_index, len(request_logs)):
                    mObj = re.search(log_msg % self.date_regex,
                                     request_logs[index])
                    if mObj:
                        #log found.
                        current_time = datetime.strptime(
                            mObj.group('date_time'), self.date_format)
                        time_taken = current_time - last_time
                        last_time = current_time
                        task_time[task] = timedelta_convertor(time_taken)
                        found = True
                        start_index = index
                        break
                if not found:
                    print "Expected log message '%(log_msg)s' not found "\
                        "for request %(request_id)s" % locals()
                    task_time[task] = 0
                    log_list.append("Expected log message '%(log_msg)s' not "\
                                    "found for request %(request_id)s" %
                                    locals())
            metrics = {'start_time': start_time,
                        'end_time': end_time,
                        'task_time': task_time}
        return metrics

    def fetch_metrics_summary(self, results_list, metrics):
        """Fetch the min, max and avg for specified metrics"""
        result = {}
        for metric in metrics:
            values = []
            for result in results_list:
                values.append(result['task_time'][metric])
            result.update({'min_%s' % metric: min(values),
                      'max_%s' % metric: max(values),
                      'avg_%s' % metric: sum(values) / len(values)})
        return result
