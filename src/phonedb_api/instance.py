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


