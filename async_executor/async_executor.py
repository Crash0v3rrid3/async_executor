import asyncio
import inspect
import logging
import os
import threading
from concurrent import futures
from contextlib import suppress
from functools import wraps
from typing import Awaitable, Tuple, AsyncGenerator, Coroutine

logger = logging.getLogger("async_executor")
__event_loops = {}


def ensure_loop():
    pid = os.getpid()
    if pid in __event_loops:
        return
    logger.debug("implicitly adding an event loop for the process {}", pid)
    set_event_loop()
    start_worker_thread()


def _func():
    loop = __event_loops[os.getpid()]
    asyncio.set_event_loop(loop)
    loop.run_forever()


def start_worker_thread():
    """Use this if you don't have a primary thread for running the event loop.
    In situations like when you use an asgi server, the primary loop is started by
    the server, so this thread *SHOULD NOT* be spawned.
    """
    # Thread locals will not be copied
    # Make sure to send all required args to the coroutine call
    __thread = threading.Thread(target=_func, name=f"looper-{os.getpid()}", daemon=True)
    __thread.start()


def set_event_loop(loop: asyncio.AbstractEventLoop = None):
    """Call this to initialize async executor.
    NOTE: Should be called once per application. This is to maintain a single
    event loop throughout the app. Also, call start_worker_thread if the app
    doesn't have a primary thread for running the async jobs
    """
    if os.getpid() in __event_loops:
        return
    logger.debug("async_executor.set_event_loop({})", str(loop))
    __event_loops[os.getpid()] = loop or asyncio.new_event_loop()


def get_event_loop():
    """Call this to initialize async executor.
    NOTE: Should be called once per application. This is to maintain a single
    event loop throughout the app.
    """
    ensure_loop()
    return __event_loops[os.getpid()]


def run_async_job(cor: Coroutine) -> futures.Future:
    """Use this to run a task asynchronously."""
    ensure_loop()
    assert asyncio.iscoroutine(cor), "A coroutine object is required!"
    if asyncio.iscoroutine(cor):
        logger.debug("async_executor.run_async_job(%s(...))", cor.cr_code.co_name)

    loop = __event_loops[os.getpid()]

    with suppress(RuntimeError):
        if asyncio.Task.current_task() is not None:
            return loop.create_task(cor)

    return asyncio.run_coroutine_threadsafe(cor, loop=loop)


def complete_async_jobs(*cors: Awaitable) -> Tuple[futures.Future, ...]:
    """Use this to optimize execution by delegating I/O tasks to async concurrency"""
    ensure_loop()
    loop = __event_loops[os.getpid()]
    logger.debug("async_executor.complete_async_jobs()")
    return asyncio.run_coroutine_threadsafe(
        asyncio.wait(cors, loop=loop),
        loop=loop,
    ).result()[0]


def agen_to_gen(agen: AsyncGenerator):
    """Async generator to generator"""
    ensure_loop()
    while True:
        try:
            yield run_async_job(agen.__anext__()).result()
        except StopAsyncIteration:
            break


def async_to_sync(cor):
    """Decorator used to convert async function to sync.
    This would do exactly what cor would, raise exceptions if any, accept the same args etc.
    """

    if inspect.isasyncgenfunction(cor):

        @wraps(cor)
        def inner(*args, **kwargs):
            yield from agen_to_gen(cor(*args, **kwargs))

        return inner

    @wraps(cor)
    def inner(*args, **kwargs):
        return run_async_job(cor(*args, **kwargs)).result()

    return inner
