from nova import exception
import tempfile

from eventlet import greenthread
from eventlet.green import subprocess
from nova import log as logging
import shlex
from nova import flags

LOG = logging.getLogger("nova.utils")
FLAGS = flags.FLAGS


def fake_rmtree(path, ignore_errors=False, onerror=None):
    raise exception.ProcessExecutionError


def rmtree_patch(name, fn):
    if name == 'shutil.rmtree':
        return fake_rmtree
    else:
        return fn


def fake_mkdtemp(suffix="", prefix='tmp', dir=None):
    raise IOError


def mkdtemp_patch(name, fn):
    if name == 'tempfile.mkdtemp':
        return fake_mkdtemp
    else:
        return fn


def fake_execute(*cmd, **kwargs):
    org_cmd = map(str, cmd)
    if org_cmd[0] == 'qemu-img':
        raise exception.ProcessExecutionError
    else:
        return execute_real(*cmd, **kwargs)


def execute_patch(name, fn):
    if name == 'nova.utils.execute':
        return fake_execute
    else:
        return fn


def execute_real(*cmd, **kwargs):
    """
    Helper method to execute command with optional retry.

    :cmd                Passed to subprocess.Popen.
    :process_input      Send to opened process.
    :check_exit_code    Defaults to 0. Raise exception.ProcessExecutionError
                        unless program exits with this code.
    :delay_on_retry     True | False. Defaults to True. If set to True, wait a
                        short amount of time before retrying.
    :attempts           How many times to retry cmd.
    :run_as_root        True | False. Defaults to False. If set to True,
                        the command is prefixed by the command specified
                        in the root_helper FLAG.

    :raises exception.InvalidInput on receiving unknown arguments
    :raises exception.ProcessExecutionError
    """

    process_input = kwargs.pop('process_input', None)
    check_exit_code = kwargs.pop('check_exit_code', 0)
    delay_on_retry = kwargs.pop('delay_on_retry', True)
    attempts = kwargs.pop('attempts', 1)
    run_as_root = kwargs.pop('run_as_root', False)
    if len(kwargs):
        msg = _('Got unknown keyword args '
                                'to utils.execute: %r') % kwargs
        LOG.error(msg)
        raise exception.InvalidInput(reason=msg)

    if run_as_root:
        cmd = shlex.split(FLAGS.root_helper) + list(cmd)
    cmd = map(str, cmd)

    while attempts > 0:
        attempts -= 1
        try:
            LOG.debug(_('Running cmd (subprocess): %s'), ' '.join(cmd))
            _PIPE = subprocess.PIPE  # pylint: disable=E1101
            obj = subprocess.Popen(cmd,
                                   stdin=_PIPE,
                                   stdout=_PIPE,
                                   stderr=_PIPE,
                                   close_fds=True)
            result = None
            if process_input is not None:
                result = obj.communicate(process_input)
            else:
                result = obj.communicate()
            obj.stdin.close()  # pylint: disable=E1101
            _returncode = obj.returncode  # pylint: disable=E1101
            if _returncode:
                LOG.debug(_('Result was %s') % _returncode)
                if type(check_exit_code) == types.IntType \
                        and _returncode != check_exit_code:
                    (stdout, stderr) = result
                    LOG.error(
                        _('%(cmd)r failed.Result was %(_returncode)s')
                                    % locals())
                    raise exception.ProcessExecutionError(
                            exit_code=_returncode,
                            stdout=stdout,
                            stderr=stderr,
                            cmd=' '.join(cmd))
            return result
        except exception.ProcessExecutionError:
            if not attempts:
                raise
            else:
                LOG.debug(_('%r failed. Retrying.'), cmd)
                if delay_on_retry:
                    greenthread.sleep(random.randint(20, 200) / 100.0)
        except EnvironmentError, e:
            if not attempts:
                LOG.error(_('%(cmd)r failed.exception: %(e)s') % locals())
                raise exception.ProcessExecutionError(
                            exit_code=e.errno,
                            stdout=None,
                            stderr=e.strerror,
                            cmd=' '.join(cmd))
            else:
                LOG.debug(_('%r failed. Retrying.'), cmd)
                if delay_on_retry:
                    greenthread.sleep(random.randint(20, 200) / 100.0)
        finally:
            # NOTE(termie): this appears to be necessary to let the subprocess
            #               call clean something up in between calls, without
            #               it two execute calls in a row hangs the second one
            greenthread.sleep(0)
