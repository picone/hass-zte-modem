"""中兴光猫API通信模块."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import base64
import html
import logging
import re
from typing import Any

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class ZTEModemAPIError(Exception):
    """中兴光猫API异常."""


class ZTEModemAPI(ABC):
    """中兴光猫API客户端基类."""

    def __init__(self, hass: HomeAssistant, host: str, username: str, password: str) -> None:
        """初始化API客户端."""
        self.hass = hass
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self._logged_in = False
        self._request_lock = asyncio.Lock()

    @property
    def session(self) -> aiohttp.ClientSession:
        """获取共享的HTTP会话."""
        return async_get_clientsession(self.hass)

    def _encrypt_password(self, password: str) -> str:
        """使用AES-CBC-PKCS7加密密码."""
        key = b"1111111111111111"
        iv = b"0000000000000000"

        # PKCS7 padding
        pad_len = 16 - (len(password) % 16)
        padded_password = password + chr(pad_len) * pad_len

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_password.encode()) + encryptor.finalize()

        return base64.b64encode(encrypted).decode()

    async def _make_request(
        self, method: str, url: str, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """统一请求方法，自动处理登录状态检查和重新登录，使用锁确保同时只有一个请求."""
        async with self._request_lock:
            # 确保已登录
            if not await self._login():
                raise ZTEModemAPIError("登录失败")

            async def _send_request() -> aiohttp.ClientResponse:
                """发送请求的内部函数."""
                return await self.session.request(method, url, **kwargs)

            # 发送请求
            async with await _send_request() as response:
                # 检查响应内容是否包含登录页面
                if response.status == 200:
                    text = await response.text()
                    if '<form name="fLogin" id="fLogin"' in text:
                        _LOGGER.warning("检测到未登录状态，重新登录")
                        self._logged_in = False
                        # 重新登录
                        if not await self._login():
                            raise ZTEModemAPIError("重新登录失败")
                        # 重新发送请求
                        async with await _send_request() as retry_response:
                            return retry_response

                return response

    async def _login(self) -> bool:
        """登录到光猫."""
        if self._logged_in:
            return True

        # 加密密码
        encrypted_password = self._encrypt_password(self.password)

        # 登录请求
        login_data = {
            "action": "login",
            "Frm_Logintoken": "0",
            "username": self.username,
            "textpwd": self.password,
            "ieversion": "1",
            "logincode": encrypted_password,
        }

        async with self.session.post(
            f"http://{self.host}/", data=login_data, allow_redirects=False
        ) as response:
            if response.status == 302:
                self._logged_in = True
                return True

            text = await response.text()
            if "其他用户正在配置" in text:
                _LOGGER.warning("其他用户正在配置设备")
                return False
            _LOGGER.error("登录失败，状态码: %s", response.status)
            return False

    @abstractmethod
    async def get_device_info(self) -> dict[str, Any] | None:
        """获取设备信息."""

    @abstractmethod
    async def get_optical_info(self) -> dict[str, Any] | None:
        """获取光模块信息."""

    @abstractmethod
    async def get_lan_info(self) -> list[dict[str, Any]] | None:
        """获取LAN口信息."""

    @abstractmethod
    async def restart_device(self) -> bool:
        """重启设备."""


class ZTESG350API(ZTEModemAPI):
    """中兴SG350光猫API实现."""

    async def get_device_info(self) -> dict[str, Any] | None:
        """获取设备信息."""
        response = await self._make_request(
            "GET", f"http://{self.host}/template.gch"
        )
        if response.status != 200:
            return None

        html_content = await response.text()

        # 提取设备信息
        device_info = {}
        patterns = {
            "carrier_name": r'<td id="Frm_CarrierName"[^>]*>([^<]+)</td>',
            "model_name": r'<td id="Frm_ModelName"[^>]*>([^<]+)</td>',
            "serial_number": r'<td id="Frm_SerialNumber"[^>]*>([^<]+)</td>',
            "hardware_ver": r'<td id="Frm_HardwareVer"[^>]*>([^<]+)</td>',
            "software_ver": r'<td id="Frm_SoftwareVer"[^>]*>([^<]+)</td>',
            "boot_ver": r'<td id="Frm_BootVer"[^>]*>([^<]+)</td>',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html_content)
            if match:
                device_info[key] = html.unescape(match.group(1).strip())

        return device_info if device_info else None

    async def get_optical_info(self) -> dict[str, Any] | None:
        """获取光模块信息."""
        url = f"http://{self.host}/getpage.gch?pid=1002&nextpage=gpon_status_link_info_t.gch"
        response = await self._make_request("GET", url)
        if response.status != 200:
            return None

        html_content = await response.text()

        # 提取光模块信息
        optical_info = {}

        # 提取功率值
        rx_power_match = re.search(r'var RxPower\s+=\s+"([^"]+)"', html_content)
        tx_power_match = re.search(r'var TxPower\s+=\s+"([^"]+)"', html_content)
        current_match = re.search(r'var Current\s+=\s+"([^"]+)"', html_content)
        volt_match = re.search(r'var Volt\s+=\s+"([^"]+)"', html_content)
        temp_match = re.search(r'var Temp\s+=\s+"([^"]+)"', html_content)

        if rx_power_match:
            rx_power_raw = int(rx_power_match.group(1))
            optical_info["rx_power"] = round(rx_power_raw / 10000, 2)

        if tx_power_match:
            tx_power_raw = int(tx_power_match.group(1))
            optical_info["tx_power"] = round(tx_power_raw / 10000, 2)

        if current_match:
            current_raw = int(current_match.group(1))
            optical_info["current"] = round(current_raw / 1000, 4)

        if volt_match:
            volt_raw = int(volt_match.group(1))
            optical_info["voltage"] = round(volt_raw / 1000000, 4)

        if temp_match:
            temp_raw = int(temp_match.group(1))
            optical_info["temperature"] = round(temp_raw / 1000, 4)

        # 提取连接状态
        loid_state_match = re.search(
            r"Transfer_meaning\('LoidState','(\d+)'\)", html_content
        )
        if loid_state_match:
            state = int(loid_state_match.group(1))
            optical_info["connected"] = state == 1
            optical_info["loid_state"] = state

        return optical_info if optical_info else None

    async def get_lan_info(self) -> list[dict[str, Any]] | None:
        """获取LAN口信息."""
        url = f"http://{self.host}/getpage.gch?pid=1002&nextpage=gpon_status_lan_info_t.gch"
        response = await self._make_request("GET", url)
        if response.status != 200:
            return None

        html_content = await response.text()

        # 解析LAN口信息
        lan_ports = []

        # 查找所有LAN口表格
        table_pattern = r'<table[^>]*class="infor"[^>]*>(.*?)</table>'
        tables = re.findall(table_pattern, html_content, re.DOTALL)

        for table_html in tables:
            port_info = {}

            # 提取端口名称
            name_match = re.search(r'<td class="tdright">(LAN\d+)</td>', table_html)
            if name_match:
                port_info["name"] = name_match.group(1)

            # 提取连接状态
            status_match = re.search(
                r'<td class="tdright">(已连接|未连接)</td>', table_html
            )
            if status_match:
                port_info["connected"] = status_match.group(1) == "已连接"

            # 提取收发包统计
            rx_match = re.search(
                r'<td class="tdright">(\d+)/(\d+)</td>', table_html
            )
            if rx_match:
                port_info["rx_packets"] = int(rx_match.group(1))
                port_info["rx_bytes"] = int(rx_match.group(2))

            # 提取发包统计（需要找到第二个匹配）
            tx_matches = re.findall(
                r'<td class="tdright">(\d+)/(\d+)</td>', table_html
            )
            if len(tx_matches) >= 2:
                port_info["tx_packets"] = int(tx_matches[1][0])
                port_info["tx_bytes"] = int(tx_matches[1][1])

            # 提取错误帧数
            error_match = re.search(r'<td class="tdright">(\d+)</td>', table_html)
            if error_match:
                # 错误帧通常是最后一个数字
                error_matches = re.findall(
                    r'<td class="tdright">(\d+)</td>', table_html
                )
                if error_matches:
                    port_info["error_frames"] = int(error_matches[-1])

            if port_info:
                lan_ports.append(port_info)

        return lan_ports if lan_ports else None

    def _parse_error_type(self, error_type_str: str) -> str:
        r"""解析错误类型字符串，处理 \x21 等字符."""
        # 处理 \x21 等转义字符，转换为对应的数值
        # \x21 = 33, \x22 = 34, 等等
        result = ""
        i = 0
        while i < len(error_type_str):
            if error_type_str[i:i+2] == "\\x":
                # 提取十六进制值
                hex_str = error_type_str[i+2:i+4]
                try:
                    hex_value = int(hex_str, 16)
                    result += str(hex_value)
                    i += 4
                except ValueError:
                    # 如果解析失败，保持原字符
                    result += error_type_str[i]
                    i += 1
            else:
                result += error_type_str[i]
                i += 1
        return result

    async def restart_device(self) -> bool:
        """重启设备."""
        # 第一步：获取 session token 和 error type
        url = f"http://{self.host}/getpage.gch?pid=1002&nextpage=manager_dev_restart_t.gch"
        response = await self._make_request("GET", url)
        if response.status != 200:
            return False

        html_content = await response.text()

        # 提取 session token
        token_match = re.search(r'var session_token = "([^"]+)"', html_content)
        if not token_match:
            _LOGGER.error("无法获取session token")
            return False

        session_token = token_match.group(1)

        # 提取 error type - 找到最后一个 Transfer_meaning('IF_ERRORTYPE','xxxx');
        error_type_pattern = r"Transfer_meaning\('IF_ERRORTYPE','([^']+)'\)"
        error_type_matches = re.findall(error_type_pattern, html_content)

        if not error_type_matches:
            _LOGGER.error("无法获取 error type")
            return False

        # 获取最后一个匹配的 error type
        error_type_raw = error_type_matches[-1]
        error_type = self._parse_error_type(error_type_raw)

        # 第二步：发送重启请求
        restart_data = {
            "IF_ACTION": "devrestart",
            "IF_ERRORSTR": "SUCC",
            "IF_ERRORPARAM": "SUCC",
            "IF_ERRORTYPE": error_type,
            "flag": "1",
            "_SESSION_TOKEN": session_token,
        }

        response = await self._make_request("POST", url, data=restart_data)
        return response.status == 200


async def detect_modem_model(hass: HomeAssistant, host: str) -> str | None:
    """检测光猫型号."""
    session = async_get_clientsession(hass)
    async with session.get(
        f"http://{host}", timeout=aiohttp.ClientTimeout(total=10)
    ) as response:
        if response.status != 200:
            return None

        text = await response.text()

        # 检测 SG350
        if "SG350" in text:
            return "SG350"

        return None


def create_api_client(
    hass: HomeAssistant, host: str, username: str, password: str, model: str | None = None
) -> ZTEModemAPI:
    """创建API客户端工厂方法."""
    if model is None:
        raise ZTEModemAPIError("未指定光猫型号")

    if model == "SG350":
        return ZTESG350API(hass, host, username, password)

    raise ZTEModemAPIError(f"不支持的光猫型号: {model}")


async def create_api_client_auto(
    hass: HomeAssistant, host: str, username: str, password: str
) -> ZTEModemAPI:
    """自动检测型号并创建API客户端."""
    model = await detect_modem_model(hass, host)
    if model is None:
        raise ZTEModemAPIError("无法检测光猫型号")

    _LOGGER.info("检测到光猫型号: %s", model)
    return create_api_client(hass, host, username, password, model)
