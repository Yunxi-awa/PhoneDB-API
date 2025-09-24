import abc
import asyncio
from typing import Callable, AsyncGenerator, Coroutine, Awaitable, Any


class AbstractAsyncRunner(abc.ABC):
    @abc.abstractmethod
    def register(self, coro: Coroutine):
        raise NotImplementedError("register method must be implemented")

    @abc.abstractmethod
    async def run(self) -> AsyncGenerator[Any, None]:
        raise NotImplementedError("run method must be implemented")


class AsyncSerialRunner(AbstractAsyncRunner):
    def __init__(self):
        self._coroutines: list[Coroutine] = []

    def register(self, coro: Coroutine):
        self._coroutines.append(coro)

    def multi_register(self, coroutines: list[Coroutine]):
        self._coroutines.extend(coroutines)

    async def run(self) -> AsyncGenerator[Any, None]:
        for task in self._coroutines:
            yield await task


class AsyncParallelRunner(AbstractAsyncRunner):
    def __init__(self, max_workers: int = 16):
        self._coroutines: list[Coroutine] = []
        self._max_workers = max_workers

    def register(self, coro: Coroutine):
        self._coroutines.append(coro)

    def multi_register(self, coroutines: list[Coroutine]):
        self._coroutines.extend(coroutines)

    async def run(self) -> AsyncGenerator[Any, None]:
        # Semaphore
        semaphore = asyncio.Semaphore(self._max_workers)

        async def sem_coro(coro: Coroutine):
            async with semaphore:
                return await coro

        result = await asyncio.gather(*[sem_coro(coro) for coro in self._coroutines])
        for task in result:
            yield task
