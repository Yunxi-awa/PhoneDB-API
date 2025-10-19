import pickle
from abc import ABC, abstractmethod
from enum import StrEnum
import re
import aiofiles.ospath
import aiofiles
import ujson
from loguru import logger

from .instance import InstMeta, InstCat, Instance


class QueryStrategy(StrEnum):
    CONTAINS = "contains"
    EQUALS = "equals"
    AT_LEAST = "at_least"
    WITHOUT_UNIT_AT_LEAST = "without_unit_at_least"

    DISPLAY_RESOLUTION_AT_LEAST = "display_resolution_at_least"


class Query:
    def __init__(self, query: str, strategy: QueryStrategy = QueryStrategy.CONTAINS):
        self.query = query
        self.strategy = strategy


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
    def search_data(self, inst_cat: InstCat, query: str) -> list[tuple[int, dict]]:
        pass

    @abstractmethod
    def query_data(self, inst_cat: InstCat, params: dict) -> list[Instance]:
        pass

    async def load(self):
        pass

    async def dump(self):
        pass


class MemoryDatabase(AbstractDatabase):
    def __init__(self):
        self._data: dict[InstCat, dict[str, dict[str, dict[str, list[str]]]]] = {}
        #                Category      ID        Section   Field    Values
        # Example: self._data[InstCat.DEVICE]["123456"]["Display"]["Resolution"] = ["1920x1080", "1366x768"]

    def get_all_data(self) -> dict:
        return self._data

    def __contains__(self, item):
        return str(item.meta.inst_id) in self._data.get(item.meta.inst_cat, {})

    def get_data(self, inst_meta: InstMeta) -> dict:
        return self._data[inst_meta.inst_cat][str(inst_meta.inst_id)]

    def add_data(self, inst_meta: InstMeta, data: dict):
        self._data.setdefault(inst_meta.inst_cat, {})[str(inst_meta.inst_id)] = data

    def clear(self):
        self._data = {}

    def search_data(self, inst_cat: InstCat, query: str) -> list[dict]:
        """
        搜索数据库中符合条件的所有数据项。

        :param inst_cat: 实例类别，用于指定搜索的实例类别。
        :param query: 查询字符串，用于匹配实例ID或数据中的内容。
        :return: 一个列表，包含所有符合条件的数据项。
        """
        # 初始化一个空列表，用于存储符合条件的数据项
        result = []

        # 获取大分类下的所有ID
        for inst_id, inst_data in self._data.get(inst_cat, {}).items():
            if inst_data["Meta"]["Image"] is None:
                continue
            for leaf in self.iter_deep_traverse(inst_data):
                if query.lower() in leaf.lower():
                    result.append((int(inst_id), inst_data))
                    break
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

    def query_data(self, inst_cat: InstCat, params: dict[str, dict[str, list[Query]]]) -> list[Instance]:
        """
        查询数据库中符合条件的所有实例元数据。

        :param inst_cat: 实例类别，用于指定查询的实例类别。
        :param params: 查询参数，用于匹配实例数据中的内容。
        :return: 一个列表，包含所有符合条件的实例元数据。
        """
        # 初始化一个空列表，用于存储符合条件的实例元数据
        result = set()
        # 遍历该类别下的所有实例
        for inst_id, inst_data in self._data.get(inst_cat, {}).items():
            for param_section, param_section_data in params.items():
                for param_field, param_values in param_section_data.items():
                    if (inst_section_data := inst_data.get(param_section)) is None:
                        break
                    if (inst_values := inst_section_data.get(param_field)) is None:
                        break
                    is_match = False
                    for param_value in param_values:
                        match param_value.strategy:
                            case QueryStrategy.CONTAINS:
                                if any(param_value.query.lower() in inst_value.lower() for inst_value in inst_values):
                                    is_match = True
                            case QueryStrategy.EQUALS:
                                if any(param_value.query.lower() == inst_value.lower() for inst_value in inst_values):
                                    is_match = True
                            case QueryStrategy.AT_LEAST:
                                if any(int(param_value.query.lower()) <= int(inst_value) for inst_value in inst_values):
                                    is_match = True
                            case QueryStrategy.WITHOUT_UNIT_AT_LEAST:
                                if any(int(param_value.query.lower()) <= int("".join(filter(lambda x: x.isdigit(), inst_value.split()))) for inst_value in inst_values):
                                    is_match = True
                            case QueryStrategy.DISPLAY_RESOLUTION_AT_LEAST:
                                for inst_value in inst_values:
                                    # 判断是否为分辨率格式
                                    try:
                                        primary_resolution, secondary_resolution = int((k:=inst_value.split("x"))[0]), int(k[1])
                                        primary_param_resolution, secondary_param_resolution = int((k:=param_value.query.split("x"))[0]), int(k[1])
                                    except ValueError:
                                        continue
                                    if primary_resolution >= primary_param_resolution and secondary_resolution >= secondary_param_resolution:
                                        is_match = True
                                        break
                    if is_match:
                        continue
                    # 执行了 break，说明该实例不符合条件
                    break
                else:   # 未执行 break，说明该实例符合条件
                    continue
                break
            else:
                result.add(
                    Instance(
                        InstMeta(inst_cat, int(inst_id)),
                        inst_data
                    )
                )
        return list(result)


class JsonDatabase(MemoryDatabase):
    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    async def load(self):
        if not await aiofiles.ospath.exists(self.filepath):
            self._data = {}
            logger.warning(f"JSON file {self.filepath} not found, skip loading.")
            return
        async with aiofiles.open(self.filepath, "r") as f:
            if (k := await f.read()) == "":
                self._data = {}
                logger.warning(f"JSON file {self.filepath} is empty, skip loading.")
                return
            self._data = ujson.loads(k)

    async def dump(self):
        async with aiofiles.open(self.filepath, "w") as f:
            await f.write(ujson.dumps(self._data, indent=2))


class PickleDatabase(MemoryDatabase):
    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    async def load(self):
        if not await aiofiles.ospath.exists(self.filepath):
            self._data = {}
            logger.warning(f"Pickle file {self.filepath} not found, skip loading.")
            return
        async with aiofiles.open(self.filepath, "rb") as f:
            if (k := await f.read()) == b"":
                self._data = {}
                logger.warning(f"Pickle file {self.filepath} is empty, skip loading.")
                return
            self._data = pickle.loads(k)

    async def dump(self):
        async with aiofiles.open(self.filepath, "wb") as f:
            await f.write(pickle.dumps(self._data))
