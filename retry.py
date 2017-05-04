"""A simple python module to add a retry function decorator"""
import functools
import itertools
import logging
import signal
import time

# Insert a comment

from decorator import decorator


class _DummyException(Exception):
    pass


class MaximumRetriesExceeded(Exception):
    pass


class MaximumTimeoutExceeded(Exception):
    pass


def _timeout(msg):
    def __internal_timeout(signum, frame):
        raise MaximumTimeoutExceeded(msg)
    return __internal_timeout


def retry(
        exceptions=(Exception,), interval=0, max_retries=10, success=None,
        timeout=-1):
    """Decorator to retry a function 'max_retries' amount of times

    :param tuple exceptions: Exceptions to be caught for retries
    :param int interval: Interval between retries in seconds
    :param int max_retries: Maximum number of retries to have, if
        set to -1 the decorator will loop forever
    :param function success: Function to indicate success criteria
    :param int timeout: Timeout interval in seconds, if -1 will retry forever
    :raises MaximumRetriesExceeded: Maximum number of retries hit without
        reaching the success criteria
    :raises TypeError: Both exceptions and success were left None causing the
        decorator to have no valid exit criteria.

    Example:
        Use it to decorate a function!

        .. sourcecode:: python

            from retry import retry

            @retry(exceptions=(ArithmeticError,), success=lambda x: x > 0)
            def foo(bar):
                if bar < 0:
                    raise ArithmeticError('testing this')
                return bar
            foo(5)
            # Should return 5
            foo(-1)
            # Should raise ArithmeticError
            foo(0)
            # Should raise MaximumRetriesExceeded
    """
    if not exceptions and success is None:
        raise TypeError(
            '`exceptions` and `success` parameter can not both be None')
    # For python 3 compatability
    exceptions = exceptions or (_DummyException,)
    _retries_error_msg = ('Exceeded maximum number of retries {} at '
                          'an interval of {}s for function {}')

    _timeout_error_msg = 'Maximum timeout of {}s reached for function {}'

    @decorator
    def wrapper(func, *args, **kwargs):
        signal.signal(
            signal.SIGALRM, _timeout(
                _timeout_error_msg.format(timeout, func.__name__)))
        run_func = functools.partial(func, *args, **kwargs)
        logger = logging.getLogger(func.__module__)
        if max_retries < 0:
            iterator = itertools.count()
        else:
            iterator = range(max_retries)
        if timeout > 0:
            signal.alarm(timeout)
        for num, _ in enumerate(iterator, 1):
            try:
                result = run_func()
                if success is None or success(result):
                    return result
            except exceptions:
                logger.exception(
                    'Exception experienced when trying function {}'.format(
                        func.__name__))
                if num == max_retries:
                    raise
            logger.warning(
                'Retrying {} in {}s...'.format(
                    func.__name__, interval))
            time.sleep(interval)
        else:
            raise MaximumRetriesExceeded(
                _retries_error_msg.format(
                    max_retries, interval, func.__name__))
    return wrapper
