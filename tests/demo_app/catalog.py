"""Explicit SDK allowlist and JSON -> typed SDK arguments. No arbitrary evaluation."""

import inspect
from dataclasses import fields
from enum import Enum
from zk_rfid import (
    ZKReader,
    InventoryConfig,
    InventoryData,
    InventoryMode,
    MemoryBank,
    TagMask,
    TagTarget,
    Region,
    QueryParameters,
    TIDParameters,
    ScanParameters,
    RealTimeConfig,
    WorkingMode,
)
from zk_rfid.errors import ValidationError

GROUPS = {
    "Reader": "get_reader_info get_serial_number get_capabilities set_address set_baudrate set_inventory_time set_interface",
    "RF & antenna": "get_power set_power get_write_power set_write_power get_write_retries set_write_retries get_antennas set_antennas get_antenna_check set_antenna_check get_region set_region get_profile set_profile get_drm set_drm",
    "Inventory": "inventory_once inventory_single inventory_matching_epc start_inventory stop_inventory",
    "Tag memory": "read_memory write_memory write_epc write_epc_single set_access_password set_kill_password lock_tag kill_tag block_write block_erase select_tag",
    "Ex10 config": "get_config set_config get_scan_parameters set_scan_parameters get_tag_focus set_tag_focus get_query_parameters set_query_parameters get_tid_parameters set_tid_parameters get_inventory_mask set_inventory_mask get_custom_profiles set_custom_profiles",
    "Real-time": "set_real_time_config get_working_mode set_working_mode get_heartbeat_interval set_heartbeat_interval",
    "Buffer": "inventory_to_buffer read_buffer get_buffer_length set_buffer_length get_buffer_count clear_buffer",
    "I/O & diagnostics": "set_buzzer pulse_indicator get_gpio set_gpio get_temperature measure_return_loss get_return_loss_threshold set_return_loss_threshold",
}
OP_GROUP = {name: group for group, names in GROUPS.items() for name in names.split()}
DESTRUCTIVE = {"kill_tag": "KILL", "lock_tag": "LOCK", "block_erase": "ERASE"}
TAG_WRITES = {
    "write_memory",
    "write_epc",
    "write_epc_single",
    "set_access_password",
    "set_kill_password",
    "block_write",
    *DESTRUCTIVE,
}
DEFAULTS = {
    "power_dbm": 20,
    "count": 1,
    "address": 0,
    "baudrate": 115200,
    "scan_time_100ms": 10,
    "interface": "uart",
    "region": {"band": 2, "min_channel": 0, "max_channel": 49},
    "profile_id": 1,
    "enabled": False,
    "active_50ms": 1,
    "silent_50ms": 1,
    "output1": False,
    "output2": False,
    "frequency_khz": 915250,
    "threshold_db": 6,
    "number": 9,
    "data": "",
    "mask": None,
    "profile_ids": [103, 241, 285],
    "interval_30s": 0,
    "max_bytes": 16,
    "bit_length": 16,
    "bit_offset": 0,
    "bank": 3,
    "word_address": 0,
    "word_count": 1,
    "target": None,
    "epc": "",
    "new_password": "",
    "kill_password": "",
    "lock_target": 4,
    "protection": 2,
}
CHOICES = {
    "interface": ["uart", "usb"],
    "baudrate": [9600, 19200, 38400, 57600, 115200],
    "max_bytes": [16, 62],
    "bank": [0, 1, 2, 3],
    "lock_target": [0, 1, 2, 3, 4],
    "protection": [0, 1, 2, 3],
    "data_kind": ["epc", "tid"],
    "number": [7, 8, 9, 10, 11, 25, 29, 31],
}
HELP = {
    "target": "Explicit full EPC or mask. TID selection should identify one physical tag.",
    "verification_target": "Post-write target if EPC or mask changes; blank keeps original target.",
    "access_password": "32-bit hex; default 00000000. Not the Kill password.",
    "word_address": "16-bit word address, decimal or 0x-prefixed hex.",
    "word_count": "Count of 16-bit words; read <=120, normal write <=32.",
    "mask": "Mask uses bit_address / bit_length; unused low bits must be zero.",
    "persist": "Save on the module; unchecked = volatile where the API offers this flag.",
    "extended_format": "null selects address format automatically for memory commands.",
    "timeout": "Overall seconds, including queue wait and multiple steps; null = SDK default.",
    "data": "Hex bytes, whole 16-bit words for tag writes.",
    "max_bytes": "Maximum stored EPC/TID length, not buffer capacity. Changing this clears buffer.",
    "profile_ids": "Three native 16-bit profile IDs; no NATION mapping.",
}
LIMITATIONS = [
    {
        "feature": "Relay / notification pulse / Range Control",
        "status": "not implemented",
        "reason": "Demo DLL exports exceed the V2.25 wire contract implemented here; exact opcode/layout still needed.",
    },
    {
        "feature": "Custom frequency table / Ex10 version query",
        "status": "not implemented",
        "reason": "Present in vendor DLL. Native SDK currently exposes region/channel tables and reader firmware only.",
    },
    {
        "feature": "MarginRead / U9 batch lock / tag LED",
        "status": "not implemented",
        "reason": "Tag-specific or newer vendor extensions; cannot infer wire format from C# DllImport.",
    },
    {
        "feature": "NXP Privacy / EAS, Monza QT, EM4325",
        "status": "unsupported",
        "reason": "Requires separate identified tag contract and protocol evidence.",
    },
    {
        "feature": "TCP/IP / network-module configuration / ISO18000-6B",
        "status": "outside scope",
        "reason": "Current SDK transport is injected async bytes + optional serial; Gen2/6C scope.",
    },
    {
        "feature": "CFG25 / CFG29",
        "status": "conditional",
        "reason": "Set requires explicit confirmed 6/5-byte dialect. Get remains raw.",
    },
    {
        "feature": "16-port getter / Scenario restore / buffer",
        "status": "conditional",
        "reason": "Unresolved mask/record-width layouts; see SDK errata. One-port module is unaffected.",
    },
    {
        "feature": "RSSI dBm / phase units / NATION RF mapping",
        "status": "conditional",
        "reason": "RSSI uses the user-defined raw - 135 mapping (60..110 to -75..-25 dBm), with raw/source/range retained. Phase follows the Ex10 demo convention. Absolute RF calibration and NATION RF equivalence remain unverified.",
    },
]


def plain(v):
    if isinstance(v, bytes):
        return v.hex().upper()
    if isinstance(v, Enum):
        return v.value
    if hasattr(v, "__dataclass_fields__"):
        return {f.name: plain(getattr(v, f.name)) for f in fields(v)}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    return v


def field_for(operation, param):
    name = param.name
    value = (
        DEFAULTS.get(name, None)
        if param.default is inspect.Parameter.empty
        else plain(param.default)
    )
    if name == "config":
        value = plain(
            RealTimeConfig()
            if operation == "set_real_time_config"
            else InventoryConfig(scan_time_100ms=10)
        )
    if name == "parameters":
        value = {
            "set_scan_parameters": plain(ScanParameters(0, 2, 4)),
            "set_query_parameters": plain(QueryParameters(4, 0)),
            "set_tid_parameters": plain(TIDParameters(0, 0)),
        }[operation]
    if name == "mask" and operation == "set_antennas":
        value = 1
    if name == "mask" and operation == "select_tag":
        value = {"bank": 2, "bit_address": 0, "bit_length": 16, "data": "E280"}
    if name == "data" and operation == "set_config":
        value = "0400"
    if name == "mode":
        value = "scenario" if operation == "start_inventory" else 0
    kind = (
        "target"
        if name in ("target", "verification_target")
        else "bool"
        if isinstance(value, bool)
        else "inventory"
        if name == "config" and operation != "set_real_time_config"
        else "json"
        if name in ("region", "parameters", "profile_ids", "config") or isinstance(value, dict)
        else "nullable_bool"
        if name == "extended_format" and value is None
        else "hex"
        if name
        in (
            "data",
            "epc",
            "access_password",
            "verification_password",
            "new_password",
            "kill_password",
        )
        else "json"
        if name == "mask" and operation != "set_antennas"
        else "number"
        if isinstance(value, (int, float)) or name in ("timeout", "power_dbm")
        else "text"
    )
    choices = CHOICES.get(name)
    if name == "mode":
        choices = (
            ["answer", "scenario", "real_time"] if operation == "start_inventory" else [0, 1, 2]
        )
    if name == "power_dbm" and operation == "set_power":
        kind = "json"
    return {
        "name": name,
        "label": name.replace("_", " "),
        "type": kind,
        "default": value,
        "choices": choices,
        "help": HELP.get(name, ""),
        "required": param.default is inspect.Parameter.empty,
    }


def catalogue():
    result = []
    for name, group in OP_GROUP.items():
        method = getattr(ZKReader, name)
        result.append(
            {
                "name": name,
                "group": group,
                "label": name.replace("_", " "),
                "description": inspect.getdoc(method) or name,
                "fields": [
                    field_for(name, p)
                    for p in inspect.signature(method).parameters.values()
                    if p.name != "self"
                ],
                "mutation": name.startswith("set_")
                or name in TAG_WRITES | {"clear_buffer", "pulse_indicator", "select_tag"},
                "tag_write": name in TAG_WRITES,
                "confirmation": DESTRUCTIVE.get(name),
            }
        )
    return result


def number(value):
    if isinstance(value, bool):
        raise ValidationError("Boolean is not a number")
    return (
        int(value, 0) if isinstance(value, str) and value.lower().startswith("0x") else int(value)
    )


def hex_bytes(value):
    if not isinstance(value, str):
        raise ValidationError("Hex value must be a string")
    try:
        return bytes.fromhex(value)
    except ValueError as e:
        raise ValidationError("Invalid hexadecimal bytes") from e


def model(cls, value):
    if not isinstance(value, dict):
        raise ValidationError(f"{cls.__name__} requires an object")
    allowed = {f.name for f in fields(cls)}
    if set(value) - allowed:
        raise ValidationError(f"Unknown {cls.__name__} fields: {set(value) - allowed}")
    v = dict(value)
    if "mask" in v and v["mask"] is not None:
        v["mask"] = model(TagMask, v["mask"])
    if cls is TagMask:
        v["data"] = hex_bytes(v["data"])
    if cls is TagTarget and v.get("epc") is not None:
        v["epc"] = hex_bytes(v["epc"])
    if cls is InventoryConfig:
        if "data" in v:
            v["data"] = InventoryData(v["data"])
        if "access_password" in v:
            v["access_password"] = hex_bytes(v["access_password"])
        if "memory_bank" in v:
            v["memory_bank"] = MemoryBank(v["memory_bank"])
    try:
        return cls(**v)
    except (ValueError, TypeError) as e:
        raise ValidationError(str(e)) from e


def convert(operation, arguments):
    if operation not in OP_GROUP:
        raise ValidationError("Operation is not in the SDK GUI allowlist")
    if not isinstance(arguments, dict):
        raise ValidationError("Arguments must be an object")
    signature = inspect.signature(getattr(ZKReader, operation))
    try:
        signature.bind(None, **arguments)
    except TypeError as e:
        raise ValidationError(str(e)) from e
    result = dict(arguments)
    for key, value in list(result.items()):
        if value is None:
            continue
        if key in (
            "access_password",
            "verification_password",
            "new_password",
            "kill_password",
            "epc",
            "data",
        ):
            result[key] = hex_bytes(value)
        elif key in ("target", "verification_target"):
            result[key] = model(TagTarget, value)
        elif key == "mask" and operation != "set_antennas":
            result[key] = model(TagMask, value)
        elif key == "region":
            result[key] = model(Region, value)
        elif key == "config":
            result[key] = model(
                RealTimeConfig if operation == "set_real_time_config" else InventoryConfig, value
            )
        elif key == "parameters":
            result[key] = model(
                {
                    "set_scan_parameters": ScanParameters,
                    "set_query_parameters": QueryParameters,
                    "set_tid_parameters": TIDParameters,
                }[operation],
                value,
            )
        elif key == "mode":
            result[key] = (
                InventoryMode(value) if operation == "start_inventory" else WorkingMode(value)
            )
        elif key == "data_kind":
            result[key] = InventoryData(value)
        elif key == "bank":
            result[key] = MemoryBank(value)
        elif key == "profile_ids" or key == "power_dbm" and isinstance(value, list):
            result[key] = tuple(value)
    return result
