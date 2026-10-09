# Phạm vi

Native host protocol ZK Gen2/6C, reader/RF/antenna/inventory/memory/buffer/I/O/diagnostics. Python async, CPython và Pyodide qua transport inject.

Ngoài scope core:6B, nghiệp vụ kiểm kho/POS, extension/service mạng dùng chung, NATION wire emulator, RF mapping tự suy đoán. Theo yêu cầu mới ngày 2026-10-09, có GUI HTML local trong tests/demo_app để gọi SDK qua CPython/serial; app này nằm ngoài core/wheel và không đổi contract transport inject. NXP/Monza-QT/EM4325 cần contract tag riêng. FastID/TagFocus opt-in, không bảo đảm tag hỗ trợ.

[Catalogue](functions_implemented.md) là implementation thực, [matrix](supported_devices.md) ghi điều kiện. License release chưa chọn; không publish/commit trong đợt này.
