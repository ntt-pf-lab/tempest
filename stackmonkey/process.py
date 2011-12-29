import subprocess
import shlex

class Process(object):
    def __init__(self, process, run_type=None):
        self.proc = process
        self.run_type = run_type
        self.proc_pid = self._get_pid()

    def _get_pid(self):
        if self.run_type == 'devstack-local':
            strip_grep = '[%s]' % self.proc[0] + self.proc[1:]
            proc1 = subprocess.Popen(shlex.split('ps aux'),
                                     stdout=subprocess.PIPE)

            proc2 = subprocess.Popen(shlex.split('grep ' + strip_grep),
                                    stdin=proc1.stdout, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            proc1.stdout.close()
            out, err = proc2.communicate()
            out = out.strip.split()
            pid = out[1]
            if not pid:
                return None
            return pid
        if not 

    def is_running_locally(self):
        if self.proc_pid
