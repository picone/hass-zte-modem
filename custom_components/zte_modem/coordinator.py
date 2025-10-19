"""数据协调器模块."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import create_api_client
from .const import (
    CONF_DEVICE_INFO,
    CONF_HOST,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ZTEModemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """中兴光猫数据协调器."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """初始化协调器."""
        self.host = config_entry.data[CONF_HOST]
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.model = config_entry.data[CONF_MODEL]
        self.device_info = config_entry.data.get(CONF_DEVICE_INFO, {})
        self.api = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"ZTE Modem {self.host}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """更新数据."""
        api = create_api_client(self.hass, self.host, self.username, self.password, self.model)

        optical_info = await api.get_optical_info()
        lan_info = await api.get_lan_info()

        return {
            "optical_info": optical_info or {},
            "lan_info": lan_info or [],
        }

    async def async_restart_device(self) -> bool:
        """重启设备."""
        api = create_api_client(self.hass, self.host, self.username, self.password, self.model)
        return await api.restart_device()
