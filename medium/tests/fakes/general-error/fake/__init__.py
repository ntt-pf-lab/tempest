from nova import exception


def fake_rmtree(path, ignore_errors=False, onerror=None):
    raise exception.ProcessExecutionError


def rmtree_patch(name, fn):
    if name == 'shutil.rmtree':
        return fake_rmtree
    else:
        return fn
