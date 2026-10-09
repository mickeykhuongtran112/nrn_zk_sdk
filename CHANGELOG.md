# Changelog

## 0.2.0.dev1 — 2026-10-09
- Gộp implementation thành một file nguồn `src/zk_rfid.py`: native API, types/errors, CRC/parser/status, command builders/decoders, async/serial transport, dispatcher, inventory và NationAdapter. Không cần generator hoặc package SDK phụ khi copy tích hợp.
- Giữ 74 method + 3 property của ZKReader, command bytes, response/error/confirmation, single RX, trace, RSSI và phase. Cập nhật demo, tools, examples, catalog và Pyodide dùng cùng file.
- Đổi import module con sang `from zk_rfid import ...`; thêm SerialTransport và NationAdapter vào public exports. Đường dẫn module cũ/pickle chứa class path cũ không còn tương thích. API vẫn async/await.
- Cấu hình wheel thành `py-modules`, thêm kiểm thử copy file độc lập bằng Python `-I -S` và chạy runtime harness không có site-packages/pyserial. Không thực hiện kiểm thử phần cứng mới trong đợt gộp file.

## 0.1.0.dev1 — 2026-10-09
- Sửa bảng tag trống khi UI mới gọi `/api/live` trên Python server cũ: fallback snapshot, báo HTTP/version/restart, tự phục hồi live và chặn snapshot đến muộn. Server giữ static assets cùng phiên; thêm regression client/HTTP.
- Thêm RSSI mapping theo yêu cầu người dùng: raw60→−75dBm, raw110→−25dBm (`raw - 135`), áp dụng cho inventory/stream/buffer; giữ raw/source/in-range, xuất qua adapter/CSV/log và cột dBm trên GUI. Ngoài dải dùng ngoại suy, không clamp.
- Sửa cập nhật tag theo đợt: HTTP live stream riêng, bộ đếm cộng dồn/resync, cập nhật ô DOM, tách log/state; Answer session phát report trước khi kết thúc vòng. Hiển thị phiên inventory thực tế và dropped reports.
- Decode phase begin/end BE16 cho các report có extension; thêm degree/radian helpers theo convention Ex10 V6.8 (0.087deg mod180), giữ raw/metadata và RSSI unsigned. GUI chọn đơn vị, CSV xuất đầy đủ; xem docs/phase_and_live_view.md.
- Đổi demo UI sang Graphite Light dựa trên UI/UX Pro Max: semantic gray tokens, SVG icons, responsive navigation, focus/keyboard cho bảng tag và log, giữ vị trí đọc log; không đổi protocol/API.
- Bổ sung HTML test console trong tests/demo_app theo yêu cầu mới: 72 thao tác + Connect/Disconnect, typed forms/JSON, simulator, inventory/tag table, CSV/JSONL và recovery theo cổng.
- Bổ sung TraceEvent/on_event và logger zk_rfid.trace cho request/TX/RX/frame/result/state; callback lỗi không phá I/O, GUI ghi file qua hàng đợi riêng.
- Đối chiếu phạm vi NATION/demo C# trong docs/demo_and_parity.md; không khẳng định đủ vendor extension chưa triển khai.
- Triển khai native Gen2 ZK frame/CRC/parser và dispatcherasync singleRX, deadline/resync/error/lifecycle.
- Triển khai reader/RF/antenna/Ex10CFG/buffer/GPIO/diagnostics; giữ các mâu thuẫn manual ở errata.
- Triển khai Answer/FastID/TID/Mix/statistics, Scenario snapshot/restore, Real-time/trigger/heartbeat, stop theo mode.
- Triển khai tag memorynormal/extended, EPC/PC/password/read-back/Select/Lock/Kill/BlockWrite/Erase; giữpartial/unknown và không retrywrite.
- Thêm SerialTransport tùy chọn, transportinject, examples/console/capture/replay/comparator.
- Thêm adapterNATIONasync và giữ nguyên reference/licensethirdparty.
- Thêm testsunit/integration/runtime/hardwareopt-in, Pyodideharness, symbolcatalogue và docs.
- Chưa hardwareverified, chưa benchmarkRF/powercycle, license phát hànhZK chưa chọn.

## 0.1.0.dev0 — 2026-10-09
- Dựng scaffold, tree và plan ban đầu; giữ nguyên dữ liệu riêng và NATIONreference.
