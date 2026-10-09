# Documented / vendor-loopback vectors
frames.json chứa8expectedTX độc lập với codec mới, nhập từ sibling reference nation-zk-python/tests/test_api.py::test_vendor_golden_frames và docs/PROTOCOL.md,2026-10-09. Nguồn lịch sử là Ex10 V6.8 UHFReader288.dll điều khiển loopback.

Đây là nguồn byteTX độc lập để kiểm CRC/format; không phảiRFcapture mới, không xác nhận firmware đang kết nối. Không cần sibling project hoặcDLL để chạy tests. CRC "123456789"=0x6F91 là check bổ sung.

RX synthetic và state-machine peer nằm tests/conftest.py; fixtures/captured giữ riêng cho capture module thật có model/firmware/điều kiện rõ. Không đổi nhãn synthetic thành captured.
