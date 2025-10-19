"""常量定义."""

DOMAIN = "zte_modem"

# 配置键
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_MODEL = "model"
CONF_DEVICE_INFO = "device_info"

# 设备信息键
DEVICE_INFO_CARRIER_NAME = "carrier_name"
DEVICE_INFO_MODEL_NAME = "model_name"
DEVICE_INFO_SERIAL_NUMBER = "serial_number"
DEVICE_INFO_HARDWARE_VER = "hardware_ver"
DEVICE_INFO_SOFTWARE_VER = "software_ver"
DEVICE_INFO_BOOT_VER = "boot_ver"

# 光模块信息键
OPTICAL_RX_POWER = "rx_power"
OPTICAL_TX_POWER = "tx_power"
OPTICAL_CURRENT = "current"
OPTICAL_VOLTAGE = "voltage"
OPTICAL_TEMPERATURE = "temperature"
OPTICAL_CONNECTED = "connected"
OPTICAL_LOID_STATE = "loid_state"

# LAN口信息键
LAN_NAME = "name"
LAN_CONNECTED = "connected"
LAN_RX_PACKETS = "rx_packets"
LAN_RX_BYTES = "rx_bytes"
LAN_TX_PACKETS = "tx_packets"
LAN_TX_BYTES = "tx_bytes"
LAN_ERROR_FRAMES = "error_frames"

# 更新间隔（秒）
UPDATE_INTERVAL = 600

# 支持的光猫型号
SUPPORTED_MODELS = ["SG350"]

# 默认型号
DEFAULT_MODEL = "SG350"
