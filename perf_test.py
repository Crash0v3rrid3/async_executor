import asyncio
import multiprocessing
import time
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

import aiohttp
from requests_futures.sessions import FuturesSession

import async_executor

async_executor.set_event_loop(asyncio.new_event_loop())


URLS = ["https://jsonplaceholder.typicode.com/posts/1", "https://www.duckduckgo.com"]


def time_this(func):
    cpu_t = time.process_time_ns()
    func()
    return time.process_time_ns() - cpu_t


async def async_api_call(url):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            "GET",
            url
        ) as request:
            await request.read()


def sync_api_call(session, url):
    return session.get(url)


def async_run_parallel(calls: int, url: str):
    return time_this(partial(async_executor.complete_async_jobs, *(async_api_call(url) for _ in range(calls))))


def sync_run_parallel(calls: int, num_workers: int, url: str):
    session = FuturesSession(executor=ThreadPoolExecutor(max_workers=num_workers))

    def _run():
        for each in [sync_api_call(session, url) for _ in range(calls)]:
            each.result()

    return time_this(_run)


def ns_to_s(t):
    return t / (10 ** 9)


AVERAGE_OF = 10
NUM_WORKERS = multiprocessing.cpu_count()
for url in URLS:
    for e in range(1, 3):
        calls = 10 ** e

        # Average of 5
        async_execution_times = [async_run_parallel(calls, url) for _ in range(AVERAGE_OF)]
        async_cpu_time_avg = sum(async_execution_times) / AVERAGE_OF

        sync_execution_times = [sync_run_parallel(calls, NUM_WORKERS, url) for _ in range(AVERAGE_OF)]
        sync_cpu_time_avg = sum(sync_execution_times) / AVERAGE_OF

        print(f"URL: {url}, API Calls: {calls}, Average of: {AVERAGE_OF}")
        print(
            f"Async CPU Time: {ns_to_s(async_cpu_time_avg)}, "
            f"Sync CPU Time: {ns_to_s(sync_cpu_time_avg)}, "
            f"Diff: {ns_to_s(async_cpu_time_avg - sync_cpu_time_avg)}"
        )
