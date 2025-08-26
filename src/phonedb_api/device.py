import datetime

import dateparser

from .item import Item


class Device(Item):
    @property
    def brand(self) -> str:
        """
        设备品牌
        """
        return self.parsed["Introduction"]["Brand"][0]

    @property
    def model(self) -> str:
        """
        设备型号
        """
        return self.parsed["Introduction"]["Model"][0]

    @property
    def released_date(self) -> datetime.datetime:
        """
        发布日期
        """
        return dateparser.parse(self.parsed["Introduction"]["Released"][0])

    @property
    def platform(self) -> str:
        """
        操作系统平台(Google Android/Apple iOS/...)
        """
        return self.parsed["Software Environment"]["Platform"][0]

    @property
    def cpu(self) -> str:
        """
        处理器
        """
        return self.parsed["Application processor, Chipset"]["CPU"][0]

    @property
    def ram_type(self) -> str:
        """
        内存类型(LPDDR5X/LPDDR5/LPDDR4X/LPDDR4/...)
        """
        return self.parsed["Application processor, Chipset"]["RAM Type"][0]

    @property
    def ram_clock(self) -> str:
        """
        内存时钟(~MHz)
        """
        return self.parsed["Application processor, Chipset"]["RAM Type"][1]

    @property
    def ram_capacity(self) -> str:
        """
        内存容量(MiB)
        """
        return self.parsed["Application processor, Chipset"]["RAM"][0]

    @property
    def nvm_type(self) -> str:
        """
        非易失性内存类型(EFlash EEPROM/...)
        """
        return self.parsed["Non-volatile Memory"]["Non-volatile Memory Type"][0]

    @property
    def nvm_interface(self) -> str:
        """
        非易失性内存接口(UFS 3.1/UFS 3.0/...)
        """
        return self.parsed["Non-volatile Memory"]["Non-volatile Memory Interface"][0]

    @property
    def nvm_capacity(self) -> str:
        """
        非易失性内存容量(MiB)
        """
        return self.parsed["Non-volatile Memory"]["Non-volatile Memory Capacity"][0]

    @property
    def display_resolution(self) -> str:
        """
        显示分辨率(px)
        """
        return self.parsed["Display"]["Resolution"][0]

    @property
    def display_area_utilization(self) -> str:
        """
        屏占比(%)
        """
        return self.parsed["Display"]["Display Area Utilization"][0]

    @property
    def display_pixel_density(self) -> str:
        """
        像素密度(dpi)
        """
        return self.parsed["Display"]["Pixel Density"][0]

    @property
    def display_type(self) -> str:
        """
        显示类型(Color AM-OLED/...)
        """
        return self.parsed["Display"]["Display Type"][0]

    @property
    def display_refresh_rate(self) -> str:
        """
        刷新频率(Hz)
        """
        return self.parsed["Display"]["Display Refresh Rate"][0]

    @property
    def audio_channel(self) -> str:
        """
        音频通道数(mono/stereo)
        """
        return self.parsed["Audio Subsystem"]["Audio Channel(s)"][0]

    @property
    def loudspeaker(self) -> str:
        """
        扬声器数量
        """
        return self.parsed["Sound Playing"]["Loudspeaker(s)"][0]

    @property
    def touchscreen_sampling_rate(self) -> str:
        """
        触摸屏采样率(Hz)
        """
        return self.parsed["Control Peripherals"]["Touchscreen Sampling rate"][0]

    @property
    def max_charging_power(self) -> str:
        """
        最大充电功率(W)
        """
        return self.parsed["Communication Interfaces"]["Max. Charging Power"][0]

    @property
    def nfc(self) -> str:
        """
        NFC
        """
        return self.parsed["Communication Interfaces"]["NFC"][0]

    @property
    def ir(self) -> str:
        """
        是否支持IR(红外)
        """
        return self.parsed["Communication Interfaces"]["IR"][0]

    @property
    def ipxx(self) -> str:
        """
        IPXX
        """
        return (f"IP"
                f"{self.parsed["Ingress Protection"]["Protection from solid materials"][0][0]}"
                f"{self.parsed["Ingress Protection"]["Protection from liquids"][0][0]}")

    @property
    def nominal_battery_capacity(self) -> str:
        """
        标称电池容量(mAh)
        """
        return self.parsed["Power Supply"]["Nominal Battery Capacity"][0]

    @property
    def nominal_battery_energy(self) -> str:
        """
        标称电池能量(Wh)
        """
        return self.parsed["Power Supply"]["Nominal Battery Energy"][0]

    @property
    def market_country(self) -> list[str]:
        """
        市场国家
        """
        return self.parsed["Geographical Attributes"]["Market Countries"][0]

    @property
    def market_region(self) -> list[str]:
        """
        市场区域
        """
        return self.parsed["Geographical Attributes"]["Market Regions"][0]
