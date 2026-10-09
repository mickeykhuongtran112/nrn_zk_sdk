"""Native asynchronous Python SDK for ZK Gen2 UHF readers."""

import logging
from .measurements import phase_to_degrees, phase_to_radians, rssi_to_dbm
from .events import TraceEvent
from .reader import ZKReader
from .capabilities import ReaderCapabilities
from .models import (
    BufferCounts,
    CommandResult,
    Confirmation,
    GPIOState,
    Heartbeat,
    InventoryConfig,
    InventoryData,
    InventoryMode,
    InventoryOutcome,
    InventoryStatistics,
    LockProtection,
    LockTarget,
    MemoryBank,
    Outcome,
    QueryParameters,
    ReaderInfo,
    ReaderState,
    RealTimeConfig,
    Region,
    ScanParameters,
    TagMask,
    TagReport,
    TagTarget,
    TIDParameters,
    WorkingMode,
    WorkingModeConfig,
    WritePower,
)
from .errors import (
    DeviceError,
    ExchangeError,
    OperationError,
    ProtocolError,
    QueueOverflow,
    RequestTimeout,
    StateError,
    TransportError,
    UnsupportedFeature,
    UnverifiedFeature,
    ValidationError,
    ZKError,
)
from .inventory_session import InventorySession
from .transports.base import AsyncTransport

__version__ = "0.1.0.dev1"
SDK_NAME = "ZK RFID SDK"
SDK_VERSION = __version__


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Opt-in SDK logger; import does not modify application logging."""
    logger = logging.getLogger("zk_rfid")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger


__all__ = [
    "rssi_to_dbm",
    "phase_to_degrees",
    "phase_to_radians",
    "ZKReader",
    "TraceEvent",
    "ReaderCapabilities",
    "InventorySession",
    "AsyncTransport",
    "CommandResult",
    "Outcome",
    "Confirmation",
    "ReaderState",
    "ReaderInfo",
    "MemoryBank",
    "TagMask",
    "TagTarget",
    "TagReport",
    "InventoryConfig",
    "InventoryData",
    "InventoryMode",
    "InventoryOutcome",
    "InventoryStatistics",
    "Heartbeat",
    "Region",
    "GPIOState",
    "RealTimeConfig",
    "WorkingMode",
    "WorkingModeConfig",
    "WritePower",
    "ScanParameters",
    "QueryParameters",
    "TIDParameters",
    "LockTarget",
    "LockProtection",
    "BufferCounts",
    "ZKError",
    "ValidationError",
    "ProtocolError",
    "StateError",
    "TransportError",
    "ExchangeError",
    "RequestTimeout",
    "UnsupportedFeature",
    "UnverifiedFeature",
    "QueueOverflow",
    "DeviceError",
    "OperationError",
    "setup_logging",
    "SDK_NAME",
    "SDK_VERSION",
    "__version__",
]
