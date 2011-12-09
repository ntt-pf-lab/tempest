import re
import subprocess
import tempfile
import time


def cleanup_virtual_instances():
    # kill still existing virtual instances.
    for line in subprocess.check_output('virsh list --all',
                                        shell=True).split('\n')[2:-2]:
        (id, name, state) = re.split('\s+', line, maxsplit=2)
        if state == 'running':
            subprocess.check_call('virsh destroy %s' % id, shell=True)
        subprocess.check_call('virsh undefine %s' % name, shell=True)


def cleanup_processes(processes):
    for process in processes:
        process.stop()
    lambda: time.sleep(10)


def emphasised_print(s, decorator='*-'):
    print(decorator * 100)
    print('')
    print(s)
    print('')
    print(decorator * 100)


def silent_check_call(*args, **kwargs):
    fake_stdout = tempfile.TemporaryFile()
    fake_stderr = tempfile.TemporaryFile()
    try:
        for (name, file) in [('stdout', fake_stdout),
                             ('stderr', fake_stderr)]:
            if name not in kwargs:
                kwargs[name] = file
        subprocess.check_call(*args, **kwargs)
    except subprocess.CalledProcessError:
        fake_stdout.seek(0)
        fake_stderr.seek(0)
        emphasised_print("STDOUT result:\n\n" + fake_stdout.read())
        emphasised_print("STDERR result:\n\n" + fake_stderr.read())
        raise
