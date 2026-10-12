"""Read-only connection discovery for the console, separate from SDK policy."""

from dataclasses import replace

from zk_rfid import ValidationError, WorkingMode, get_power

# Ex10 V6.8 Form1.GetRDVersionAntennaChipType reads these ReaderType.ini entries.
# Names describe that vendor table; product labels are not a wire capability.
READER_TYPES = {
    0x71: ("UHF7180M", 1),
    0x73: ("UHF7181M", 4),
    0x75: ("UHF7182M", 4),
    0x76: ("UHF7189M", 8),
    0x77: ("UHF7199M", 16),
}


async def detect_ports(reader):
    """Use 0x21 model code, cross-checked against 0x94 per-port power in Answer."""
    info = (await reader.get_reader_info()).require_success()
    model, expected = READER_TYPES.get(info.model_code, (None, None))
    mode = (await reader.get_working_mode()).require_success().mode
    detected = expected
    source = "reader_info"
    if mode is WorkingMode.ANSWER:
        if expected:
            reader.capabilities = replace(reader.capabilities, antenna_ports=expected)
        power = await reader.get_power()
        # A valid 0x94 response may fail the initial declared-length decoder.
        # Preserve that result in the trace and validate its full raw payload.
        if power.status != 0:
            power.require_success()
        detected = len(power.raw_data)
        if detected not in (1, 4, 8, 16):
            raise ValidationError(
                f"Cannot detect antenna ports: 0x94 returned {detected} power bytes"
            )
        get_power(ports=detected).decode(power.raw_data)
        if expected and detected != expected:
            raise ValidationError(
                f"Reader type 0x{info.model_code:02X} ({model}) declares {expected} ports, "
                f"but 0x94 returned {detected}. Check the device variant; reconnect with "
                "automatic detection disabled only after confirming the physical port count."
            )
        source = "reader_info_and_power" if expected else "power_response"
    elif expected is None:
        raise ValidationError(
            f"Unknown reader type 0x{info.model_code:02X}; power discovery is unavailable "
            "in Real-time/Trigger mode. Select the verified port count manually and reconnect."
        )
    firmware = ".".join(f"{part:02d}" for part in info.firmware)
    reader.capabilities = replace(
        reader.capabilities,
        antenna_ports=detected,
        model=model or reader.capabilities.model,
        firmware=firmware,
    )
    return {
        "ports": detected,
        "ports_source": source,
        "model_code": info.model_code,
        "reported_model": model,
        "firmware": firmware,
    }
