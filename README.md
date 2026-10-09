# ZK RFID SDK

SDK Python native async cho ZK-7180M/ZK-7182M thuộc họ Ex10, phạm vi RAIN UHF Gen2/ISO18000-6C. Core tự tạo và giải mã protocol ZK, không phụ thuộc DLL hãng hoặc driver NATION.

**Đã triển khai SDK và GUI kiểm thử; chưa nghiệm thu toàn bộ phần cứng.** Ngoài 3 hardware tests PASS do người dùng cung cấp, đã kiểm tra Scenario có phase trên COM13/115200/1-port: 7.594 reports, Stop thành công, hiển thị RSSI dBm và phase. Xem [biên bản kiểm tra trên module thật](docs/hardware_live_view_check.md).

- [Danh mục function/class/constant và chữ ký API](docs/functions_implemented.md): sinh từ mã nguồn, theo dạng Symbols yêu cầu.
- [GUI demo: cài đặt, thao tác COM13, log và mô phỏng](tests/demo_app/README.md).
- [Đối chiếu mức đầy đủ với NATION và demo C# ZK](docs/demo_and_parity.md).
- [API và contract kết quả](docs/api.md), [ma trận hỗ trợ](docs/supported_devices.md).
- [Kiểm thử](docs/validation.md), [nguồn và errata](docs/protocol/errata.md).
- [Adapter NATION](docs/nation_comparison.md), [kế hoạch](plan_agent.md).

## Cài đặt

Python >=3.11. Core không có dependency ngoài; serial là extra của CPython.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,serial]"
.\.venv\Scripts\python -m pytest -q
```

```python
import asyncio
from zk_rfid import ZKReader, ReaderCapabilities, InventoryConfig
from zk_rfid.transports.serial import SerialTransport

async def main():
    async with ZKReader(
        SerialTransport("COM13", 115200),  # Thay bằng cổng/baud thực tế.
        capabilities=ReaderCapabilities(antenna_ports=1),
        timeout=3.0,
    ) as reader:
        print((await reader.get_reader_info()).require_success())
        result = await reader.inventory_once(InventoryConfig(scan_time_100ms=3))
        for tag in result.reports:
            print(tag.epc, tag.tid, tag.rssi_raw)
        print(result.termination_reason, result.complete)

asyncio.run(main())
```

Import/constructor không mở COM. Một reader sở hữu một transport và một RX task. Pyodide inject transport async; cùng source đã chạy qua [harness](tests/runtime/README.md).

## GUI thử nghiệm

```powershell
.\.venv\Scripts\python.exe -m tests.demo_app --port COM13 --baud 115200 --ports 1
```

Mở http://127.0.0.1:8765. Connect mở COM; chọn Simulated reader để thử không cần phần cứng. Đủ đường gọi 74 public method (72 trong menu + open/close), log native TX/RX/status, bảng EPC/TID và export JSONL/CSV. Xem [hướng dẫn](tests/demo_app/README.md).

## Chức năng

| Nhóm | Đã triển khai |
|---|---|
| Core | CRC/frame/parser, resync có diagnostics, deadline, single RX, serial tùy chọn |
| Reader | Info/serial/address/baud/scan time/interface |
| Inventory | Answer EPC/TID/FastID/Mix, single/match EPC, statistics, Scenario, Real-time/trigger/heartbeat, stop theo mode |
| Tag | Read/write normal/extended, mask/full EPC, PC/EPC/password, read-back, Select/Lock/Kill/BlockWrite/Erase |
| RF | Power chung/từng port, write power/retry, antenna mux/check, region/channel/profile16bit/DRM |
| Ex10 | CFG7/8/9/10/11/31; CFG25/29 có điều kiện xác nhận dialect |
| Buffer/I/O | Inventory/read/count/clear/length, GPIO/LED/buzzer, temperature/return loss |
| Tools | Examples, console/capture/replay/comparator, xuất symbols, HTML test console và structured trace |
| NATION | Baseline nguyên trạng; adapter async giữ native result/error, không tự map RF |

Các giới hạn cụ thể ở ma trận hỗ trợ, đặc biệt CFG25/29, Mix>31word và một số layout16port. SDK không suy ra capability tag/antenna từ tên chip E710.

## Kiểm chứng và phát hành

```powershell
python -m ruff check src tests tools examples
python -m ruff format --check src tests tools examples
python -m pytest -q
python tools/compare_results.py
python tools/export_symbols.py --check
python -m build
```

Hardware tests mặc định bị loại; cần chỉ định COM và điều kiện tag. License phát hành mã ZK chưa chọn; LICENSE được giữ nguyên. MIT của NATION chỉ áp dụng bản tham chiếu đó. Chưa phát hành package lên PyPI.

local_data/ được ignore, không là dependency của core/tests và không đóng gói. GUI cục bộ trong tests/demo_app là phần mở rộng theo yêu cầu mới; HTTP/threads nằm ngoài core và wheel SDK.
