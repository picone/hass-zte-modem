"""中兴光猫集成."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import ZTEModemCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# 服务定义
SERVICE_RESTART_DEVICE = "restart_device"

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置条目."""
    coordinator = ZTEModemCoordinator(hass, entry)

    # 获取初始数据
    await coordinator.async_config_entry_first_refresh()

    # 存储协调器
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 注册服务
    async def async_restart_device_service(call: ServiceCall) -> None:
        """处理重启设备服务调用."""
        config_entry_id = call.data["config_entry_id"]

        # 直接通过配置条目ID获取协调器
        coordinator = hass.data[DOMAIN].get(config_entry_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for config entry: %s", config_entry_id)
            raise HomeAssistantError(f"Configuration entry {config_entry_id} not found")

        _LOGGER.info("Starting ZTE modem device restart for %s", coordinator.host)
        success = await coordinator.async_restart_device()

        if success:
            _LOGGER.info("Restart command sent successfully")
        else:
            _LOGGER.error("Failed to send restart command")
            raise HomeAssistantError("Failed to send restart command")

    # 注册服务
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_DEVICE,
        async_restart_device_service,
        schema=SERVICE_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置条目."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SERVICE_RESTART_DEVICE)

    return unload_ok
