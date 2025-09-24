import enum
from abc import ABC, abstractmethod

from loguru import logger


class LangCode(enum.StrEnum):
    EN_US = "en_US"
    ZH_CN = "zh_CN"

    @property
    def class_name(self):
        return f"LangClass{self.value[0].upper()}{self.value[1]}{self.value[2:]}"


class LangClass(ABC):
    """
    语言基类
    """
    _map = {}

    @property
    @abstractmethod
    def code(self):
        """
        :return: 语言代码, 例如 EN_US, zh_CN
        """
        pass

    @property
    def translations(self) -> dict[str, str]:
        """
        :return: 翻译文本字典
        """
        return self._map

    def translate(self, key: str) -> str:
        """获取翻译文本，支持格式化参数"""
        if key not in self.translations:
            logger.warning(f"在语言 {self.code} 中未找到键 {key}")
            return key
        else:
            return self.translations[key]

    def __getitem__(self, key: str) -> str:
        """支持通过下标访问翻译"""
        return self.translate(key)


class LangClassEnUS(LangClass):
    _map = {}

    @property
    def code(self):
        return "EN_US"

    def translate(self, key: str) -> str:
        return key

class LangClassZhCN(LangClass):
    _map = {
        "Introduction": "介绍",
        "Brand": "品牌",
        "Model": "型号",
        "Brief": "简介",
        "Released": "发售日期",
        "Announced": "发布日期",
        "Hardware Designer": "硬件设计",
        "Codename": "代号",
        "General Extras": "一般额外功能",
        "Device InstanceCategory": "设备类型",
        "List of Additional Features": "额外功能",

        "Physical Attributes": "物理信息",
        "Width": "宽度",
        "Height": "高度",
        "Depth": "厚度",
        "Bounding Volume": "包围盒体积",
        "Mass": "重量",

        "Software Environment": "软件信息",
        "Platform": "OS平台",
        "Operating System": "OS版本",
        "Software Extras": "软件额外功能",

        "Application processor, Chipset": "CPU子系统",
        "CPU Clock": "CPU 时钟",
        "CPU": "CPU",

        "Operative Memory": "RAM",
        "RAM Type": "RAM类型",
        "RAM Capacity": "RAM容量",

        "Non-volatile Memory": "ROM",
        "Non-volatile Memory Type": "ROM类型",
        "Non-volatile Memory Interface": "ROM接口",
        "Non-volatile Memory Capacity": "ROM容量",

        "Display": "屏幕",
        "Display Hole": "屏幕开孔",
        "Display Diagonal": "屏幕对角线",
        "Resolution": "分辨率",
        "Display Width": "显示宽度",
        "Display Height": "显示高度",
        "Horizontal Full Bezel Width": "水平全边框宽度",
        "Display Area": "显示面积",
        "Display Area Utilization": "屏占比",
        "Pixel Size": "像素尺寸",
        "Pixel Density": "像素密度",
        "Display Type": "屏幕类型",
        "Display Color Depth": "色深",
        "Number of Display Scales": "色阶",
        "Display Dynamic Range Depth": "动态范围深度",
        "Display Illumination": "背光类型",
        "Display Light Reflection Mode": "强反射模式",
        "Display Subpixel Scheme": "子像素方案",
        "Display Refresh Rate": "刷新率",
        "Scratch Resistant Screen": "防刮屏",

        "Graphical Subsystem": "GPU子系统",
        "Graphical Controller": "GPU",

        "Audio/Video Interfaces": "A/V接口",
        "A/V Out": "A/V输出",

        "Audio Subsystem": "音频子系统",
        "Audio Channel(s)": "声道",

        "Sound Recording": "录音",
        "Microphone(s)": "麦克风",

        "Sound Playing": "功放",
        "Loudspeaker(s):": "扬声器",
        "Audio Output:": "音频输出",

        "Cellular Phone": "无线通信",
        "Supported Cellular Bands": "支持的频段",
        "Supported Cellular Data Links": "支持的数据链接",
        "SIM Card Slot": "SIM卡槽",
        "Cellular Antenna": "天线",
        "Call Alert Sound": "来电铃声",
        "Complementary Phone Services": "补充通信服务",
        "Cellular Controller": "基带",
        "Secondary Cellular Phone": "副卡",
        "Dual Cellular Network Operation": "双卡操作",
        "Sec. Supported Cellular Networks:": "副卡支持的频段",
        "Sec. Supported Cellular Data Links:": "副卡支持的数据链接",
        "Sec. SIM Card Slot": "副卡SIM卡槽",
        "Sec. Phone Controller IC:": "副卡基带",

        "Control Peripherals": "操控外设",
        "Touchscreen Type": "触屏类型",
        "Touchscreen Simultaneous Touch Points": "多点触控",
        "Touchscreen Sampling rate": "触控采样率",

        "Communication Interfaces": "外部接口",
        "Expansion Interfaces": "扩展接口",
        "USB": "USB",
        "USB Services": "USB服务",
        "USB Connector": "USB连接器",
        "Max. Charging Power": "最大充电功率",
        "Bluetooth": "蓝牙",
        "Bluetooth profiles": "蓝牙配置",
        "Wireless LAN": "WLAN",
        "Wireless Services": "无线服务",
        "NFC": "NFC",
        "IR": "红外",

        "Multimedia Broadcast": "多媒体广播",
        "FM Radio Receiver": "FM广播",

        "Satellite Navigation": "卫星导航",
        "Supported GPS protocol(s)": "支持的GPS协议",
        "Satellite Antenna:": "卫星天线",
        "Complementary Satellite Services": "补充卫星服务",
        "Supported GLONASS protocol(s)": "支持的GLONASS协议",
        "Supported Galileo service(s)": "支持的Galileo服务",
        "Supported BeiDou system (BDS)": "支持的北斗协议",
        "Navigation Controller": "导航基带",

        "Primary Camera System": "主摄子系统",
        "Camera Placement": "主摄位置",
        "Camera Module": "摄像头模组",
        "Camera Image Sensor": "摄像头图像传感器",
        "Image Sensor Format": "摄像头图像传感器尺寸",
        "Image Sensor Pixel Size": "摄像头图像传感器像素尺寸",
        "Camera Resolution": "摄像头分辨率",
        "Number of effective pixels": "摄像头有效像素数",
        "Aperture (W)": "光圈(W)",
        "Zoom": "变焦",
        "Focus": "对焦",
        "Min. Equiv. Focal Length": "最小等效焦距",
        "Recordable Image Formats": "摄像头可拍摄图像格式",
        "Video Recording": "视频录制元数据",
        "Recordable Video Formats": "摄像头可录制视频格式",
        "Flash": "闪光灯",
        "Camera Extra Functions": "摄像头额外功能",

        "Auxiliary Camera": "子摄子系统",
        "Aux. Camera Image Sensor": "子摄图像传感器",
        "Aux. Cam. Image Sensor Format": "子摄图像传感器尺寸",
        "Aux. Cam. Image Sensor Pixel Size": "子摄图像传感器像素尺寸",
        "Aux. Camera Number of Pixels": "子摄像素数",
        "Aux. Camera Aperture (W)": "子摄光圈 (W)",
        "Aux. Camera Extra Functions": "子摄额外功能",
        "Auxiliary Camera No. 2": "子摄 2",
        "Aux. 2 Camera Image Sensor": "子摄 2 图像传感器",
        "Auxiliary Camera No. 3": "子摄 3",
        "Aux. 3 Camera Image Sensor": "子摄 3 图像传感器",
        "Auxiliary Camera No. 4": "子摄 4",
        "Aux. 4 Camera Image Sensor": "子摄 4 图像传感器",
        "Aux. 4 Camera Focus": "子摄 4 对焦",

        "Secondary Camera System": "前置摄像头系统",
        "Secondary Camera Placement": "前置摄像头位置",
        "Secondary Camera Sensor": "前置摄像头传感器",
        "Secondary Image Sensor Pixel Size": "前置图像传感器像素尺寸",
        "Secondary Camera Resolution": "前置摄像头分辨率",
        "Secondary Camera Number of pixels": "前置摄像头像素数",
        "Secondary Aperture (W)": "前置摄像头光圈 (W)",
        "Secondary Recordable Image Formats": "前置可录制图像格式",
        "Secondary Video Recording": "前置视频录制",
        "Secondary Recordable Video Formats": "前置可录制视频格式",
        "Secondary Camera Extra Functions": "前置摄像头额外功能",
        "Secondary Auxiliary Camera": "前置辅助摄像头",
        "Sec. Aux. Cam. Image Sensor": "前置辅助摄像头图像传感器",
        "Secondary Auxiliary Camera No. 2": "前置辅助摄像头 2",
        "Sec. Aux. 2 Cam. Image Sensor": "前置辅助摄像头 2 图像传感器",
        "Built-in Sensors": "内置传感器",
        "Built-in compass": "内置罗盘",
        "Built-in accelerometer": "内置加速计",
        "Built-in gyroscope": "内置陀螺仪",
        "Additional sensors": "其他传感器",
        "Ingress Protection": "防护等级",
        "Protection from solid materials": "固体防护",
        "Protection from liquids": "液体防护",
        "Immersion into liquids (depth limit)": "液体浸入（深度限制）",
        "Immersion into liquids time limit": "液体浸入（时间限制）",
        "Power Supply": "电源",
        "Battery": "电池",
        "Nominal Cell Capacity (1st cell)": "标称电芯容量（第一电芯）",
        "Nominal Battery Capacity": "标称电池容量",
        "Power Supply Controller IC": "电源控制器 IC",
        "Geographical Attributes": "地理信息",
        "Market Countries": "销售国家",
        "Market Regions": "销售地区",
        "Price": "价格",
        "Datasheet Attributes": "数据表属性",
        "Data Integrity": "数据完整性",
        "Added": "添加日期",

        "Meta": "元信息",
        "ID": "ID",
        "Image": "图片"
    }

    @property
    def code(self):
        return "zh_CN"
