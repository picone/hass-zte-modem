"""配置流程模块."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import create_api_client, detect_modem_model
from .const import CONF_DEVICE_INFO, CONF_MODEL, DOMAIN, SUPPORTED_MODELS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", default="192.168.1.1"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required("username", default="CMCCAdmin"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required("password"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """验证用户输入的数据."""
    # 检测光猫型号
    model = await detect_modem_model(hass, data["host"])
    if not model:
        raise CannotConnect("无法检测光猫型号")

    if model not in SUPPORTED_MODELS:
        raise CannotConnect(f"不支持的光猫型号: {model}")

    # 使用检测到的型号创建API客户端
    api = create_api_client(hass, data["host"], data["username"], data["password"], model)

    # 尝试登录并获取设备信息
    device_info = await api.get_device_info()
    if not device_info:
        raise CannotConnect("无法获取设备信息")

    return {
        "title": f"ZTE Modem {model} ({data['host']})",
        CONF_DEVICE_INFO: device_info,
        "model": model,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理配置流程."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """处理初始步骤."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # 将检测到的型号和设备信息添加到配置数据中
                config_data = user_input.copy()
                config_data[CONF_MODEL] = info["model"]
                config_data[CONF_DEVICE_INFO] = info[CONF_DEVICE_INFO]

                return self.async_create_entry(
                    title=info["title"],
                    data=config_data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """连接错误."""
