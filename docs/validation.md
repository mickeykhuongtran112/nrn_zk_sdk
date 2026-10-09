# Xác minh SDK — 0.2.0.dev1

Đợt gộp ngày 2026-10-09 dùng file nguồn duy nhất `src/zk_rfid.py`. Kiểm thử lại CPython/Pyodide và đóng gói; không gửi lệnh phần cứng mới. Phiên COM13 mô tả dưới đây là chứng cứ của bản `0.1.0.dev1` trước khi gộp. Đối chiếu AST khi chuyển cấu trúc giữ nguyên 161 class/function cấp module và toàn bộ method body, ngoại trừ thông báo hướng dẫn cài pyserial.
Ngày 2026-10-09; cập nhật đợt GUI/observability và kiểm tra live trên module thật. Ngoài simulator và ảnh3hardwaretestsPASS của người dùng, agent đã chạy một phiên Scenario/phase trên COM13/115200/1-port, kiểm tra RSSI mapping/live/counter và Stop. Không ghi memory tag; kết quả giới hạn ở phiên đọc này, chưa nghiệm thu RF/toàn bộ API. Xem [biên bản kiểm tra](hardware_live_view_check.md).

## Kết quả thực tế

| Kiểm tra | Môi trường / kết quả |
|---|---|
| Unit/integration/compat/runtime | CPython 3.14.6, Windows; 177 passed, 6 hardware tests deselected; gồm file độc lập, live stream/phase, RSSI mapping và HTTP assets giữ nguyên theo phiên |
| Demo client regression | Node: 6 passed; legacy404 fallback, reconnect, snapshot đến muộn, selection/clear/generation và lỗiHTTP non-JSON |
| Hardware live view | COM13/115200/1-port, Scenario có phase: 7.594 reports, 14 ID/antenna entries; Stop success, dropped=0. Cửa sổ HTTP khoảng3giây: 74 updates, median40,21ms; UI và CSV có RSSI dBm/phase |
| Ruff check / format | Pass trên src, tests, tools, examples |
| Symbol catalogue | 74 method + 3 property của ZKReader; 411 symbol trong file SDK; hợp nhất 3 khai báo TypeVar T thành 1, không bỏ API chức năng; sinh AST và --check |
| Pyodide thực | npm pyodide314.0.7, Python3.14.2/Emscripten; cùng8vector,2000fragmentedRXframes; inventory/read-back/cancellation pass,0leakedtasks |
| NATION comparator | 3 pass (hex, power dictionary, expected ZK TX),0fail,2unverified (RF profile/RSSI) |
| Package build | Wheel py3-none-any và sdist build thành công |
| Copy file độc lập | Python -I -S ở thư mục tạm, chỉ có zk_rfid.py và dữ liệu/harness kiểm thử; 8 vectors, 2000 frames, type hints/pickle/cancellation; không site-packages hoặc module SDK con |
| Cài wheel độc lập | Venv mới, --no-deps; import zk_rfid.py và chạy runtime harness mà không cài pyserial/nrn |
| Contents audit | Wheel chỉ có zk_rfid.py và metadata; không package con/manual/DLL/local_data/dữ liệu riêng/nrn.py. Sdist có tests và reference NATION + license để chạy baseline hash tests |
| GUI catalogue/API | 72 thao tác + Connect/Disconnect, typed arguments, target/write guards, loopback/token/origin, job/error/recovery được kiểm thử |
| Observability | Correlation request/chunk/frame/result; observer exception; timeout UNKNOWN; bounded JSONL/CSV |
| CLI smoke | Tất cả examples và tools --help chạy được mà không mở phần cứng |

CI workflow dành cho Python3.11/3.14 và Pyodide. Run GitHub của commit đầu bị chặn trước khi chạy job do billing của tài khoản; các kết quả trong bảng được kiểm chứng tại môi trường local. Minimum3.11 là contract package; môi trường local được chạy ở3.14.6. Không suy ra mọi OS/browser đã verified.

## Những hành vi đã kiểm thử

- CRC8goldenTX độc lập và check6F91; parser mọi điểm chia chunk, nhiều frame, noise/CRC/bounded recovery.
- Pending trướcTX, immediate response, một RX duy nhất khi gọi đồng thời, short writes, wrong address, broadcast, stale reply, EOF, cancel/timeout và resync gate.
- Native statuses, FC nested tag errors, persistence13partial, payload thành công sai length không false success.
- Answer multi-frame/statistics/no-tag/device-timeout; FastID/TID/phase; Mix sequence/thiếu memory; Scenario snapshot/restore, report trướcstartACK và saustopACK, queue overflow.
- Real-time command whitelist/heartbeat;93 không ACK và không deadlock; stop51 theoACK.
- Word/bit/address/payload bounds; write/read-back/mismatch; PC bảo toàn11bit; target trước/sauEPC/password; hủy verify vẫn giữACK, không retrywrite.
- Deadline toàn chuỗi và chờlock; buffer counts/multi-frame/partial/cancel.
- NATION baseline source/LICENSE hash; adapter power giữ port khác và bảo toàn native error; không suy đoánRF.
- GUI: simulated native config/inventory/Scenario restore/read-back; F9, FC/04, 13, host timeout; recovery gate theo cổng tồn tại qua phiên simulator; direct working-mode stop/disconnect.
- GUI tag recovery: kiểm tra read-only server8765 cũ (`/api/live`404, snapshot25dòng/8.375reports); frontend sửa đã hiển thị lại25dòng. Server mới8766 với simulator hiển thịlive, raw85→−50dBm, phase22.272°/44.544° hoặc256/512; chọn target giữ qua cập nhật. Không gửi lệnh tới COM13 trong đợt này.
- Core không import serial/threading/OS/subprocess; runtime lifecycle đóng sạch trong harness hữu hạn.

Bộ tests không phải exhaustive cho mọi model/firmware/CRC-collision/timing. Fixture RX/state peer là synthetic; goldenTX có nguồn historicalDLLloopback, không được gọi là hardwarecapture mới.

## Chạy lại

```powershell
python -m pip install -e ".[dev,serial]"
python -m ruff check src tests tools examples
python -m ruff format --check src tests tools examples
python -m pytest -q
node --test tests/browser/demo_client.test.cjs
python tools/export_symbols.py --check
python tools/compare_results.py
python -m build
npm install --prefix local_data/pyodide pyodide@314.0.7
node tests/runtime/run_pyodide.mjs local_data/pyodide/node_modules/pyodide/pyodide.mjs
```

Không có dependency vào siblingproject/manual/DLL để chạy bộ testCPython. Pyodide được tải riêng cho harness, không phải runtime dependency củawheel.

## Hardware và nghiệm thu còn lại

Mặc định pytest loại markerhardware. Chỉ chạy sau khi chọn cổng, model/firmware và điều kiệnRF:

```powershell
$env:ZK_HARDWARE_PORT = "COM13"
$env:ZK_ANTENNA_PORTS = "1"
$env:ZK_BAUDRATE = "115200"
$env:ZK_MODEL = "ten-model-thuc"
$env:ZK_FIRMWARE = "revision-thuc"
python -m pytest -m hardware tests/hardware/test_reader_config.py
```

Các bài inventory phátRF; Scenario thay cấu hình tạm vàrestore. Test Userwrite còn yêu cầu ZK_ALLOW_TAG_WRITE=1, ZK_TEST_TID và tag thử nghiệm cóUserbank; khôi phục dữ liệu cũ chỉ khi connection còn biết chắc trạng thái. Test suite không tự chạyKill/permanentLock.

Còn phải thu trace model/firmware cụ thể, kiểmpersistence qua mất nguồn, write đúngtag, timingstop/lateEE, errataCFG25/29/16port và benchmarkRF theo [inventory_benchmark.md](inventory_benchmark.md). Không dùng report/s để chứng minh completeness hoặc uniqueEPC để suy sốphysicaltag.

License phát hành mãZK chưa chọn. Không publish hoặc commit. Xem [ma trận hỗ trợ](supported_devices.md) và [errata](protocol/errata.md) trước nghiệm thu.

## GUI browser smoke (simulator)

Đã thao tác trực tiếp trên browser: kết nối simulator; get_reader_info lặp; FastID hiện EPC/TID; Scenario start/stop về idle; chọn TID, User write và read_back_verified; native FC/04 hiển thị failure/tag_error; export CSV và JSONL được đọc lại kiểm tra. Render/parse JSON thành công cả 72 form, không có lỗi JavaScript trong các luồng đã thử. Bố cục panel hẹp và desktop hai cột được kiểm tra; dữ liệu đều synthetic, không phải capture COM13. Các chức năng phụ thuộc chip/firmware chưa được simulator mô hình hóa không được coi là đã test phần cứng.
