import aiofiles
import ujson

from .instance import InstMeta, InstCat
from abc import ABC, abstractmethod


class AbstractDatabase(ABC):
    @abstractmethod
    def get_all_data(self) -> dict:
        pass

    @abstractmethod
    def __contains__(self, item):
        pass

    @abstractmethod
    def get_data(self, inst_meta: InstMeta) -> dict:
        pass

    @abstractmethod
    def add_data(self, inst_meta: InstMeta, data: dict):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def search_data(self, query: str, inst_cat: InstCat) -> list[dict]:
        pass

    async def load(self):
        pass

    async def dump(self):
        pass


class MemoryDatabase(AbstractDatabase):
    def __init__(self):
        self._data = {}

    def get_all_data(self) -> dict:
        return self._data

    def __contains__(self, item):
        return str(item.inst_id) in self._data.get(item.inst_cat, {})

    def get_data(self, inst_meta: InstMeta) -> dict:
        return self._data[str(inst_meta.inst_cat)][str(inst_meta.inst_id)]

    def add_data(self, inst_meta: InstMeta, data: dict):
        self._data.setdefault(inst_meta.inst_cat, {})[str(inst_meta.inst_id)] = data

    def clear(self):
        self._data = {}

    def search_data(self, query: str, inst_cat: InstCat) -> list[dict]:
        """
        搜索数据库中符合条件的所有数据项。

        :param inst_cat: 实例类别，用于指定搜索的实例类别。
        :param query: 查询字符串，用于匹配实例ID或数据中的内容。
        :return: 一个列表，包含所有符合条件的数据项。
        """
        # 初始化一个空列表，用于存储符合条件的数据项
        result = []

        for inst_id, data in self._data.get(inst_cat, {}).items():
            for leaf in self.iter_deep_traverse(data):
                if query in leaf:
                    result.append(data)
        return result

    @staticmethod
    def iter_deep_traverse(data):
        """
        一个高效的非递归深度遍历工具，用于遍历嵌套的字典和列表。

        :param data: 需要遍历的嵌套对象，可以是字典、列表或它们的组合。
        :yield: 对象中的每一个叶子项。
        """
        # 初始化一个栈，并将初始对象放入其中
        stack = [data]

        # 当栈不为空时，持续循环
        while stack:
            # 从栈顶取出一个元素
            current_node = stack.pop()

            # 如果当前元素是字典，则将其所有的值（非键）压入栈中
            if isinstance(current_node, dict):
                for value in current_node.values():
                    stack.append(value)
            # 如果当前元素是列表或元组，则将其所有元素逆序压入栈中
            # 逆序是为了在pop时能够保持原始的遍历顺序
            elif isinstance(current_node, (list, tuple)):
                stack.extend(reversed(current_node))
            # 如果当前元素不是字典或列表，那么它就是一个叶子项
            else:
                yield current_node


class JsonDatabase(MemoryDatabase):
    def __init__(self, json_file: str):
        super().__init__()
        self.json_file = json_file

    async def load(self):
        async with aiofiles.open(self.json_file, "r") as f:
            if (k:=await f.read()) == "":
                self._data = {}
                return
            self._data = ujson.loads(k)

    async def dump(self):
        async with aiofiles.open(self.json_file, "w") as f:
            await f.write(ujson.dumps(self._data, indent=2))
