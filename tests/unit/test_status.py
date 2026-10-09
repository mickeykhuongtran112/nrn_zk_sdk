from zk_rfid.protocol.status import interpret_status
from zk_rfid import Outcome


def test_context_specific_status():
    assert not interpret_status(1, 3).terminal
    assert interpret_status(1, 2).outcome is Outcome.PARTIAL
    assert interpret_status(0x21, 1).outcome is Outcome.FAILURE
    assert interpret_status(0xEE, 0x28).name == "heartbeat"
    assert not interpret_status(0xEE, 0x28).terminal
    assert interpret_status(0x03, 0xFC, b"\x04").tag_error == 4
    assert interpret_status(0x02, 0xFB).name == "no_tag"
    assert interpret_status(0x03, 0xFA).name == "tag_communication_error"
    assert interpret_status(0x2F, 0x13).outcome is Outcome.PARTIAL
    assert "unknown_status" in interpret_status(0x21, 0xAB).name
