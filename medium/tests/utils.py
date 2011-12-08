import tempfile
import subprocess


def emphasised_print(s):
    print('*-' * 60)
    print('')
    print(s)
    print('')
    print('*-' * 60)


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
