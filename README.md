# Async Executor
An async task executor implementation for the entire app.
Integrate this with sync apps to take advantage of async concurrency.

This is useful in sync applications like Django,
where I/O calls an be delegated to the async executor 
from multiple threads to take advantage of async concurrency.
This reduces the overall CPU time.

I've written a simple script(perf_test.py) to test the performance difference. 
```
URL: https://jsonplaceholder.typicode.com/posts/1, API Calls: 10, Average of: 10
Async CPU Time: 0.0255071238, Sync CPU Time: 0.1154297789, Diff: -0.08992265510000001

URL: https://jsonplaceholder.typicode.com/posts/1, API Calls: 100, Average of: 10
Async CPU Time: 0.25864718659999997, Sync CPU Time: 0.4066750969, Diff: -0.14802791029999998

URL: https://www.duckduckgo.com, API Calls: 10, Average of: 10
Async CPU Time: 0.1006329721, Sync CPU Time: 0.3036486956, Diff: -0.20301572350000002

URL: https://www.duckduckgo.com, API Calls: 100, Average of: 10
Async CPU Time: 0.5598390416, Sync CPU Time: 1.1786238077, Diff: -0.6187847661
```

It uses two clients(aiohttp & requests) for making HTTP API calls to two urls.
In order to use multithreading for parallel calls, the script uses requests-futures with
ThreadPoolExecutor with max workers as cpu count.

The result shows the CPU usage time(in seconds) of both taking an average of 10 runs.
As the I/O response time increases(for larger response payload sizes), the CPU time for the sync version increases greatly
in comparision to the async one.

## API
```python
def set_event_loop(event_loop: AbstractEventLoop):
    """Call this at app init to set the event loop"""

def get_event_loop():
    """This returns the event loop set by `set_event_loop` that is currently being used by the executor."""

def run_async_job(cor: Coroutine) -> concurrent.futures.Future:
    """Use this to execute an async job from a synchronous thread.
    To get the result of the execution, call `concurrent.futures.Future.result` on the
    returned object. This will block the thread until the async job completes.
    
    `concurrent.futures.Future.result` will raise an exception if the coroutine raises one.
    """

def complete_async_jobs(*cors: Awaitable) -> Tuple[concurrent.futures.Future, ...]:
    """Use this to run multiple async jobs parallelly. 
    This returns only when all the provided awaitables complete their execution.
    Use `concurrent.futures.Future.result` to access the result or exception of 
    an individual coroutine.
    """

def async_to_sync(coroutinefunction) -> Callable:
    """A simple async to sync decorator."""

def agen_to_gen(async_generator) -> Generator:
    """Used to convert an async generator to a sync one."""
```
