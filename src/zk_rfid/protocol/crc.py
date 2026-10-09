"""UART CRC: reflected 0x8408, init FFFF, no xorout, low byte first."""

from .constants import CRC16_INIT, CRC16_POLY


def crc16(data: bytes, initial: int = CRC16_INIT) -> int:
    crc = initial
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (CRC16_POLY if crc & 1 else 0)
    return crc & 0xFFFF


def append_crc(data: bytes) -> bytes:
    return data + crc16(data).to_bytes(2, "little")
