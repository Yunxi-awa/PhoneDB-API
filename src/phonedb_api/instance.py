import dataclasses
import enum


class InstCat(enum.StrEnum):
    """
    实例分类
    """
    DEVICE = "device"
    FIRMWARE = "repository"
    PROCESSOR = "processor"
    OS = "opsys"
    MOBILE_OPERATOR = "vendor"


@dataclasses.dataclass
class InstMeta:
    """
    实例元数据
    """
    inst_cat: InstCat
    inst_id: int

class Instance:
    def __init__(self, meta: InstMeta, data: dict):
        self.meta = meta
        self.data = data

    def __str__(self):
        return f"Instance(inst_cat={self.meta.inst_cat}, inst_id={self.meta.inst_id})"

    def __hash__(self):
        return hash((self.meta.inst_cat, self.meta.inst_id))



