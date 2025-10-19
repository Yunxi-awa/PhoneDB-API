import abc
import asyncio
import os
from typing import Callable, AsyncGenerator, Coroutine, Awaitable, Any


class AbstractAsyncRunner(abc.ABC):
    @abc.abstractmethod
    def register(self, coro: Awaitable[Any]):
        pass

    @abc.abstractmethod
    async def run(self) -> AsyncGenerator[Any, None]:
        pass


class AsyncSerialRunner(AbstractAsyncRunner):
    def __init__(self):
        self._coroutines: list[Awaitable[Any]] = []

    def register(self, coro: Awaitable[Any]):
        self._coroutines.append(coro)

    def register_multi(self, coroutines: list[Awaitable[Any]]):
        self._coroutines.extend(coroutines)

    async def run(self) -> AsyncGenerator[Any, None]:
        for task in self._coroutines:
            yield await task
        self._coroutines.clear()


class AsyncParallelRunner(AbstractAsyncRunner):
    def __init__(self, max_workers: int = os.process_cpu_count()):
        self._coroutines: list[Awaitable[Any]] = []
        self._max_workers = max_workers or 32

    def register(self, coro: Awaitable[Any]):
        self._coroutines.append(coro)

    def register_multi(self, coroutines: list[Awaitable[Any]]):
        self._coroutines.extend(coroutines)

    async def run(self) -> AsyncGenerator[Any, None]:
        # Semaphore
        semaphore = asyncio.Semaphore(self._max_workers)

        async def sem_coro(coro: Awaitable[Any]):
            async with semaphore:
                return await coro

        for task in asyncio.as_completed((sem_coro(coro) for coro in self._coroutines)):
            yield await task
        self._coroutines.clear()
