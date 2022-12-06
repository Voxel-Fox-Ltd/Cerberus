from typing import AsyncGenerator, TypeVar, Generic
import asyncio


__all__ = (
    "alist",
    "adict",
)


T = TypeVar("T")


class alist(list, Generic[T]):

    def __init__(self, current, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extend(current)

    async def __aiter__(self) -> AsyncGenerator[T, None]:
        for i in self:
            await asyncio.sleep(0)
            yield i


class adict(dict):

    def __init__(self, current, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(current)

    def items(self):
        return alist(super().items())
