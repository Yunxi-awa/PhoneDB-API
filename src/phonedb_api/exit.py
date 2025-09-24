import atexit
import asyncio
import threading
import time


class AsyncExitManager:
    def __init__(self):
        self._loop = None
        self._thread = None
        self._tasks = []

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _stop_loop(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()

    def register(self, task):
        if not asyncio.iscoroutinefunction(task):
            raise TypeError("Task must be an async function")
        self._tasks.append(task)
        atexit.register(self.shutdown)

    def shutdown(self):
        if self._tasks:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            for task in self._tasks:
                asyncio.run_coroutine_threadsafe(task(), self._loop)

            self._loop.call_soon_threadsafe(lambda: self._loop.call_later(0, self._loop.stop))
            self._thread.join()


async_exit = AsyncExitManager()


# async def async_cleanup_1():
#     print("Executing async cleanup task 1...")
#     await asyncio.sleep(1)
#     print("Async cleanup task 1 finished.")
#
#
# async def async_cleanup_2():
#     print("Executing async cleanup task 2...")
#     await asyncio.sleep(2)
#     print("Async cleanup task 2 finished.")
#
#
# async_exit.register(async_cleanup_1)
# async_exit.register(async_cleanup_2)
#
# print("Program is running...")
# time.sleep(3)
# print("Program is exiting...")