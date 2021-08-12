import asyncio
import inspect
from contextlib import contextmanager
from threading import local

from async_executor import async_to_sync

_state = local()


@contextmanager
def force_async():
    """Use this to force AsyncToSyncMixin.__getattr__ to always return a coroutine.
    Useful for running multiple calls asynchronously in the primary thread at a time.
    """
    try:
        _state.force_async = True
        yield
    finally:
        _state.force_async = False


def get_current_task():
    """
    Cross-version implementation of asyncio.current_task()

    Returns None if there is no task.
    """
    try:
        if hasattr(asyncio, "current_task"):
            # Python 3.7 and up
            return asyncio.current_task()
        else:
            # Python 3.6
            return asyncio.Task.current_task()
    except RuntimeError:
        return None


def _should_wrap(item):
    return asyncio.iscoroutinefunction(item) or inspect.isasyncgenfunction(item)


class AsyncToSyncMixin:
    """A utility to patch any class with async API to work with sync code.
    It patches the __getattribute__ method to decide whether to return a coroutine to
    the caller or to return a function which wraps the coroutine, runs it and returns it
    result once done. It does this based on two parameters
    - Is the force_async context enabled or
    - Is the current execution happening under an async task in the primary event loop.

    Useful when working with sync frameworks like Django and you want take full advantage of
    async concurrency.
    """
    # To avoid conflicts with base classes
    __slots__ = ()

    def __enter__(self):
        try:
            enter = super().__enter__
        except AttributeError as e:
            try:
                enter = async_to_sync(super().__aenter__)
            except AttributeError:
                raise e
        return enter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            exit_ = super().__exit__
        except AttributeError as e:
            try:
                exit_ = async_to_sync(super().__aexit__)
            except AttributeError:
                raise e
        return exit_(exc_type, exc_val, exc_tb)

    def __getattribute__(self, name):
        item = super().__getattribute__(name)

        if _should_wrap(item) is False:
            return item

        if (
            getattr(_state, "force_async", False) is True
            or get_current_task() is not None
        ):
            return item
        return async_to_sync(item)


__all__ = ["AsyncToSyncMixin", "force_async"]
