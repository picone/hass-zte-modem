"""传感器实体模块."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfInformation,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_INFO,
    DEVICE_INFO_HARDWARE_VER,
    DEVICE_INFO_MODEL_NAME,
    DEVICE_INFO_SERIAL_NUMBER,
    DEVICE_INFO_SOFTWARE_VER,
    DOMAIN,
    LAN_CONNECTED,
    LAN_ERROR_FRAMES,
    LAN_NAME,
    LAN_RX_BYTES,
    LAN_RX_PACKETS,
    LAN_TX_BYTES,
    LAN_TX_PACKETS,
    OPTICAL_CONNECTED,
    OPTICAL_CURRENT,
    OPTICAL_RX_POWER,
    OPTICAL_TEMPERATURE,
    OPTICAL_TX_POWER,
    OPTICAL_VOLTAGE,
)
from .coordinator import ZTEModemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器实体."""
    coordinator: ZTEModemCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # 光模块传感器
    entities.extend(
        [
            OpticalConnectionSensor(coordinator, config_entry),
            OpticalRxPowerSensor(coordinator, config_entry),
            OpticalTxPowerSensor(coordinator, config_entry),
            OpticalCurrentSensor(coordinator, config_entry),
            OpticalVoltageSensor(coordinator, config_entry),
            OpticalTemperatureSensor(coordinator, config_entry),
        ]
    )

    # LAN口传感器
    if coordinator.data and "lan_info" in coordinator.data:
        for lan_port in coordinator.data["lan_info"]:
            if LAN_NAME in lan_port:
                port_name = lan_port[LAN_NAME]
                entities.extend(
                    [
                        LanConnectionSensor(coordinator, config_entry, port_name),
                        LanRxPacketsSensor(coordinator, config_entry, port_name),
                        LanRxBytesSensor(coordinator, config_entry, port_name),
                        LanTxPacketsSensor(coordinator, config_entry, port_name),
                        LanTxBytesSensor(coordinator, config_entry, port_name),
                        LanErrorFramesSensor(coordinator, config_entry, port_name),
                    ]
                )

    async_add_entities(entities)


class ZTEModemSensor(CoordinatorEntity[ZTEModemCoordinator], SensorEntity):
    """中兴光猫传感器基类."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry) -> None:
        """初始化传感器."""
        super().__init__(coordinator)

        # 从config_entry中获取设备信息
        device_info = config_entry.data.get(CONF_DEVICE_INFO, {})
        host = config_entry.data["host"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"ZTE Modem {host}",
            manufacturer="ZTE",
            model=device_info.get(DEVICE_INFO_MODEL_NAME, None),
            serial_number=device_info.get(DEVICE_INFO_SERIAL_NUMBER, None),
            sw_version=device_info.get(DEVICE_INFO_SOFTWARE_VER, None),
            hw_version=device_info.get(DEVICE_INFO_HARDWARE_VER, None),
        )


class OpticalConnectionSensor(ZTEModemSensor):
    """光口连接状态传感器."""

    _attr_translation_key = "optical_connection"
    _attr_unique_id = "optical_connection"
    _attr_icon = "mdi:connection"

    @property
    def native_value(self) -> str | None:
        """返回连接状态."""
        optical_info = self.coordinator.data.get("optical_info", {})
        if OPTICAL_CONNECTED in optical_info:
            return "Connected" if optical_info[OPTICAL_CONNECTED] else "Disconnected"
        return None


class OpticalRxPowerSensor(ZTEModemSensor):
    """光模块输入功率传感器."""

    _attr_translation_key = "optical_rx_power"
    _attr_unique_id = "optical_rx_power"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float | None:
        """返回输入功率."""
        optical_info = self.coordinator.data.get("optical_info", {})
        return optical_info.get(OPTICAL_RX_POWER)


class OpticalTxPowerSensor(ZTEModemSensor):
    """光模块输出功率传感器."""

    _attr_translation_key = "optical_tx_power"
    _attr_unique_id = "optical_tx_power"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float | None:
        """返回输出功率."""
        optical_info = self.coordinator.data.get("optical_info", {})
        return optical_info.get(OPTICAL_TX_POWER)


class OpticalCurrentSensor(ZTEModemSensor):
    """光模块电流传感器."""

    _attr_translation_key = "optical_current"
    _attr_unique_id = "optical_current"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.MILLIAMPERE
    _attr_icon = "mdi:current-ac"

    @property
    def native_value(self) -> float | None:
        """返回电流值."""
        optical_info = self.coordinator.data.get("optical_info", {})
        return optical_info.get(OPTICAL_CURRENT)


class OpticalVoltageSensor(ZTEModemSensor):
    """光模块电压传感器."""

    _attr_translation_key = "optical_voltage"
    _attr_unique_id = "optical_voltage"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float | None:
        """返回电压值."""
        optical_info = self.coordinator.data.get("optical_info", {})
        return optical_info.get(OPTICAL_VOLTAGE)


class OpticalTemperatureSensor(ZTEModemSensor):
    """光模块温度传感器."""

    _attr_translation_key = "optical_temperature"
    _attr_unique_id = "optical_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """返回温度值."""
        optical_info = self.coordinator.data.get("optical_info", {})
        return optical_info.get(OPTICAL_TEMPERATURE)


class LanConnectionSensor(ZTEModemSensor):
    """LAN口连接状态传感器."""

    _attr_translation_key = "lan_connection"
    _attr_icon = "mdi:ethernet"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口连接传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} Connection Status"
        self._attr_unique_id = f"lan_{port_name.lower()}_connection"

    @property
    def native_value(self) -> str | None:
        """返回连接状态."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                if LAN_CONNECTED in port:
                    return "Connected" if port[LAN_CONNECTED] else "Disconnected"
        return None


class LanRxPacketsSensor(ZTEModemSensor):
    """LAN口接收包数传感器."""

    _attr_translation_key = "lan_rx_packets"
    _attr_native_unit_of_measurement = "packets"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:download"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口接收包数传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} RX Packets"
        self._attr_unique_id = f"lan_{port_name.lower()}_rx_packets"

    @property
    def native_value(self) -> int | None:
        """返回接收包数."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                return port.get(LAN_RX_PACKETS)
        return None


class LanRxBytesSensor(ZTEModemSensor):
    """LAN口接收字节数传感器."""

    _attr_translation_key = "lan_rx_bytes"
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:download"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口接收字节数传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} RX"
        self._attr_unique_id = f"lan_{port_name.lower()}_rx_bytes"

    @property
    def native_value(self) -> int | None:
        """返回接收字节数."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                return port.get(LAN_RX_BYTES)
        return None


class LanTxPacketsSensor(ZTEModemSensor):
    """LAN口发送包数传感器."""

    _attr_translation_key = "lan_tx_packets"
    _attr_native_unit_of_measurement = "packets"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:upload"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口发送包数传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} TX Packets"
        self._attr_unique_id = f"lan_{port_name.lower()}_tx_packets"

    @property
    def native_value(self) -> int | None:
        """返回发送包数."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                return port.get(LAN_TX_PACKETS)
        return None


class LanTxBytesSensor(ZTEModemSensor):
    """LAN口发送字节数传感器."""

    _attr_translation_key = "lan_tx_bytes"
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:upload"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口发送字节数传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} TX"
        self._attr_unique_id = f"lan_{port_name.lower()}_tx_bytes"

    @property
    def native_value(self) -> int | None:
        """返回发送字节数."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                return port.get(LAN_TX_BYTES)
        return None


class LanErrorFramesSensor(ZTEModemSensor):
    """LAN口错误帧数传感器."""

    _attr_translation_key = "lan_error_frames"
    _attr_native_unit_of_measurement = "frames"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: ZTEModemCoordinator, config_entry: ConfigEntry, port_name: str) -> None:
        """初始化LAN口错误帧数传感器."""
        super().__init__(coordinator, config_entry)
        self.port_name = port_name
        self._attr_name = f"{port_name} Error Frames"
        self._attr_unique_id = f"lan_{port_name.lower()}_error_frames"

    @property
    def native_value(self) -> int | None:
        """返回错误帧数."""
        lan_info = self.coordinator.data.get("lan_info", [])
        for port in lan_info:
            if port.get(LAN_NAME) == self.port_name:
                return port.get(LAN_ERROR_FRAMES)
        return None
