import dataclasses
import enum

from bs4 import BeautifulSoup
from loguru import logger

from .language import LangClass


def split_by_commas(s):
    parts = []
    start = 0
    depth = 0

    for i, char in enumerate(s):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(s[start:i].strip())
            start = i + 1

    parts.append(s[start:].strip())
    return parts


class ItemCategory(enum.StrEnum):
    DEVICE = "device"
    FIRMWARE = "repository"
    PROCESSOR = "processor"
    OS = "opsys"
    MOBILE_OPERATOR = "vendor"

    def __call__(self, id_spec: int) -> "ItemInfo":
        return ItemInfo(category=self, id_spec=id_spec)


@dataclasses.dataclass
class ItemInfo:
    category: ItemCategory
    id_spec: int


class Item:
    def __init__(
            self,
            item_info: ItemInfo,
            html: str = None,
            parsed: dict[str, dict[str, list]] = None
    ):
        if parsed is None and html is None:
            raise ValueError(f"{self} 没有正确获取信息")
        self.item_info = item_info
        self._html = html
        self._parsed = parsed

    @property
    def html(self):
        return self._html

    @property
    def parsed(self) -> dict[str, dict[str, list]]:
        if self._parsed is not None:
            return self._parsed

        soup = BeautifulSoup(self._html, 'lxml')
        results = {}
        for tr in soup.select_one("table").select('tr'):
            tds = tr.find_all('td')

            match len(tds):
                case 1:
                    h = tr.find_all(['h4', 'h5'])
                    strong = tr.find('strong')
                    if h:
                        field = h[0].get_text(strip=True).replace(':', '')
                        results[field] = {}
                    elif strong:
                        pre_outer_key = tuple(results.keys())[-1]
                        field = strong.get_text(strip=True)
                        value = [i.strip() for i in split_by_commas(list(tds[0].children)[-1].get_text(strip=True))]
                        results[pre_outer_key][field] = value
                    else:
                        raise ValueError(f"Invalid tr structure: {tr}")
                case 2:
                    pre_outer_key = tuple(results.keys())[-1]

                    field = tds[0].get_text(strip=True)
                    if field:
                        value = [i.strip() for i in split_by_commas(tds[1].get_text(strip=True))]
                    else:
                        field = tuple(results[pre_outer_key].keys())[-1]
                        value = results[pre_outer_key][field] + [tds[1].get_text(strip=True)]
                    results[pre_outer_key][field] = value

        results["id"] = self.item_info.id_spec
        self._parsed = results

        return results

    def translated(self, language: LangClass) -> dict[str, dict[str, list]]:
        result = {}  # 初始化一个新的空字典
        stack: list[tuple[
            dict[str, dict[str, list]] | dict[str, list],
            dict[str, dict[str, list]] | dict[str, list]
        ]] = [(self._parsed, result)]  # 栈中存放元组：(原始字典, 新字典的对应位置)

        while stack:
            # 从栈中取出 (原始子字典, 新子字典的对应位置)
            old_sub_dict, new_sub_dict = stack.pop()

            for key, value in old_sub_dict.items():
                # logger.debug(f"翻译 {key}")
                new_key = language.translate(key)  # 为当前键创建新键

                # 如果值是字典，需要为其在新的字典中创建一个子字典
                if isinstance(value, dict):
                    new_sub_dict[new_key] = {}
                    # 将子字典添加到栈中，以便后续处理
                    stack.append((value, new_sub_dict[new_key]))
                else:
                    # 如果值不是字典，直接将新键和值添加到新的字典中
                    new_sub_dict[new_key] = value

        return result

    def __repr__(self) -> str:
        return f"Item({self.item_info.category}: {self.item_info.id_spec})"
