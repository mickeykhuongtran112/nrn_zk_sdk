# ZK SDK Test Console

Ứng dụng HTML chạy cục bộ, nằm trong `tests/demo_app`. Python sở hữu COM và gọi SDK; trình duyệt chỉ gửi yêu cầu tới `127.0.0.1`. Không cần Node, npm, WebSerial, DLL hãng hoặc framework web.

Demo import cùng file nguồn [src/zk_rfid.py](../../src/zk_rfid.py) dùng khi tích hợp; không có bản SDK riêng cho GUI. Sau khi nâng lên bản một file `0.2.0.dev1`, cài lại editable install và restart Python server theo lệnh dưới đây. Reload trình duyệt không thay thế restart server Python.

Giao diện **Graphite Light** dùng tông xám nhẹ, tham khảo Minimalism & Swiss Style của UI/UX Pro Max. Xem [theme, tokens và kết quả kiểm tra UI](DESIGN.md). Khi đã mở app trước lúc đổi theme, reload trang để tải CSS/JS mới.

## Chạy trên máy đang nối COM13

Tại thư mục gốc project, trong PowerShell:

```powershell
cd D:\Firmware-Develop\Nextwaves_middleware_sdk\zk-rfid-sdk
.\.venv\Scripts\python.exe -m pip install -e ".[serial]"
.\.venv\Scripts\python.exe -m tests.demo_app --port COM13 --baud 115200 --ports 1
```

Trình duyệt mở [http://127.0.0.1:8765](http://127.0.0.1:8765). Có thể mở URL này thủ công. Nếu cổng HTTP bận, thêm `--http-port 8766`; nếu không muốn tự mở browser, thêm `--no-browser`.

1. Đóng kết nối của demo C# / serial terminal trước khi dùng cùng COM13.
2. Chọn COM13, 115200, Ports=1, địa chỉ module thực tế (mặc định 0). **Bỏ chọn Simulated reader** để dùng phần cứng. Bấm **Connect**. Connect chỉ mở transport, không tự đổi RF power/region.
3. Nhóm **Reader** → `get_reader_info` → **Send command**; sau đó `get_serial_number`. Kiểm tra Command result và Transaction log.
4. Nhóm **RF & antenna** → `get_power`, `get_antennas`, `get_region`, `get_profile`. Với module một port: antenna ID=1, mask=1. Đọc giá trị hiện tại trước khi sửa.
5. Nhóm **Inventory** → `inventory_once`: Data=epc, Antenna=1; gửi để đọc một vòng. Chọn fastid/tid/mix khi tag/firmware hỗ trợ; mục TID / Mix / mask chứa địa chỉ, số word, password và mask. Quan sát số report và bảng tag, không chỉ chữ SUCCESS.
6. Để đọc liên tục: `start_inventory`, mode=scenario (hoặc answer/real_time theo nhu cầu), Antenna=1 → Send. Bấm **Stop inventory** để kết thúc và xem kết quả stop/restore.
7. Nhóm **Tag memory**: bấm dòng tag để lấy EPC/TID làm target; chọn `read_memory`, bank, word address/count và access password. Khi ghi, điền dữ liệu hex, bật `verify` nếu có và **Enable this tag write**. Lock/Kill/Erase yêu cầu gõ LOCK/KILL/ERASE; `write_epc_single` yêu cầu xác nhận chỉ có một tag trong vùng đọc.
8. **Export CSV** xuất bảng tag được giữ; **Export JSONL** xuất lịch sử gần nhất. Log đầy đủ hơn được ghi xoay vòng tại `local_data/demo_logs/`.
9. Bấm **Stop inventory**, **Disconnect**; `Ctrl+C` trong terminal để tắt server.

Nếu mất phản hồi sau TX, kết quả có thể là UNKNOWN. Không tự gửi lại một lệnh ghi. Dừng/đóng kết nối, xác lập ranh giới sạch phía thiết bị (ví dụ reset/power cycle rồi chờ module ổn định), chọn **Capabilities & recovery → Module reset / clean wire boundary established**, rồi Connect. Checkbox là xác nhận của người vận hành, không thực hiện reset thiết bị. Trạng thái không chắc được giữ theo cổng trong vòng đời server; không thay thế việc xử lý module sau khi restart app.

## Tất cả chức năng SDK trong GUI

Danh mục allowlist có kiểm thử tự động so với tất cả phương thức public của `ZKReader`: **72 thao tác + open/close qua Connect/Disconnect = 74 phương thức**. Không gọi tùy ý thuộc tính Python từ HTTP.

| Nhóm | Số thao tác | Nội dung |
|---|---:|---|
| Reader | 7 | Info, serial, capabilities, address, baud, scan time, interface |
| RF & antenna | 16 | Power/read-write power/retry, antenna mask/check, region, profile, DRM |
| Inventory | 5 | One round, single tag, EPC match, managed start/stop |
| Tag memory | 11 | Read/write, EPC, access/kill password, lock/kill, block write/erase, Select |
| Ex10 config | 14 | Raw CFG, scan/query/TID/mask/custom profiles, TagFocus |
| Real-time | 5 | Saved config, mode get/set, heartbeat |
| Buffer | 6 | Inventory to buffer, read/count/clear, length get/set |
| I/O & diagnostics | 8 | Buzzer, indicator, GPIO, temperature, return loss/threshold |

**All APIs** liệt kê toàn bộ. Mỗi thao tác có mô tả lấy từ SDK, form chuyển đúng kiểu dữ liệu và **Advanced JSON arguments** cho cấu trúc phức tạp. JSON chỉ thay thế tham số sau khi bấm **Use this JSON**; chọn lại thao tác để quay về form. Form dùng số thập phân hoặc `0x...`, trường bytes dùng hex không có `0x`. Địa chỉ memory tính bằng word 16 bit; mask tính bằng bit.

Các API không phải mọi thao tác đều dùng chung CommandResult: capabilities trả metadata; start trả session; stop/inventory/buffer trả InventoryOutcome. GUI giữ nguyên kiểu kết quả đó và không giả status ACK cho Connect hay start session.

`start_inventory(mode="real_time")` quản lý iterator và stop. `set_working_mode` là cấu hình mode lưu trên reader: nếu gọi trực tiếp, các frame 0xEE xuất hiện trong log nhưng chưa có session để giải mã vào bảng tag. Nút Stop sẽ gửi `set_working_mode(ANSWER)` khi app biết reader đang ở Real-time/Trigger mà không có session. Disconnect cũng cố dừng mode này và ghi kết quả. Saved mode “unknown” nghĩa là chưa đọc mode; lifecycle “idle” chỉ là trạng thái host, không chứng minh RF đã tắt trên module vừa kết nối.

## Log, kết quả và trạng thái

- Mỗi job có ID, operation, tham số, thời điểm, result hoặc loại lỗi. “ACCEPTED” chỉ là server nhận việc.
- Trace SDK: request → TX chunk đã được transport chấp nhận → RX chunk → frame CRC hợp lệ → response complete → result. Exchange ID nối request/response của một giao dịch; RX thô có thể chứa nhiều frame nên không gán bừa một ID.
- Result giữ `outcome`, `command`, `status`, `tag_error`, `raw_data`, `confirmation`, `diagnostics`, `steps`. Các trường có trong kiểu trả về tương ứng được xuất nguyên vẹn.
- SUCCESS, FAILURE, PARTIAL và UNKNOWN được hiển thị riêng. ACKNOWLEDGED khác READ_BACK_VERIFIED. Xem [đối chiếu và ví dụ status](../../docs/demo_and_parity.md).
- Có state transitions, timeout, parser loss, lỗi queue/consumer, exception và fault kết nối. Nếu consumer lỗi, app cố stop session và log cả kết quả stop.
- Reader lifecycle lấy từ SDK; saved mode lấy từ phản hồi/mutation đã xác nhận. Không tự polling lệnh thiết bị: polling HTTP chỉ đọc snapshot của host.
- Trace giữ nguyên bytes. RSSI có cột raw và dBm theo mapping người dùng `raw - 135` (60→−75,110→−25), dấu* chỉ ngoại suy ngoài60..110; CSV/JSON giữ source/in-range. Phase tách begin/end, chọn degrees/radians/raw integer; quy đổi theo demo Ex10 V6.8, có nguồn và metadata. Không gọi thời gian host là RF timing. Xem [phase, RSSI và live view](../../docs/phase_and_live_view.md).
- Mất heartbeat trình duyệt quá 30 giây: app cố dừng inventory/mode mà nó quản lý. Đóng/mất browser không thay thế Stop trong tình huống tiến trình/USB bị hỏng.

Lịch sử RAM: 5.000 events; GUI giữ 1.200, hiển thị tối đa 200 dòng log; xuất JSONL là 5.000 events được giữ cùng metadata. File JSONL: 10 MB/file và 3 bản xoay vòng; hàng đợi disk 20.000 events, không chặn RX. Drop/disk error hiển thị trên GUI. CSV xuất tối đa 5.000 ID/antenna entries được giữ, bảng hiển thị 1.000 đầu; overflow đếm rõ. Kết nối mới xóa bảng tag để không trộn tag mô phỏng với phần cứng. Pause view chỉ ngừng tải/vẽ log trên browser; RX và disk log tiếp tục.

Luồng tag dùng HTTP NDJSON riêng, đẩy thay đổi với tổng đếm hiện tại, tối đa khoảng30lần/giây; log và snapshot trạng thái chạy riêng. Client chậm/reconnect nhận số đếm cộng dồn, không phát lại từng bước giả. Answer session đưa report ngay từ frame trung gian; Scenario dùng reportEE. `Active session` hiển thị phiên thực tế, khác với Saved mode hoặc lựa chọn chưa gửi trên form. Khi cập nhật code Python cần Stop/Disconnect, tắt server cũ, chạy lại rồi Ctrl+F5 trang.

Nếu `/api/live` không hỗ trợ hoặc bị ngắt, bảng tự dùng snapshot (khoảng750ms + thời gianHTTP) và báo đúng chế độ. HTTP404 từ server cũ cần restartPython để có live/RSSI/phase mới; refresh trang đơn thuần không đủ. Khi mạng hồi phục, số đếm đồng bộ từ live và không bị snapshot cũ ghi đè. Server giữ HTML/JS/CSS theo phiên lúc khởi động, nên sau khi sửa frontend cũng cần restart. GUI hiển thị cảnh báo khi revisionAPI không khớp.

Raw TX/RX và tham số ghi có thể chứa password tag/EPC/TID; log này cố ý giữ nguyên phục vụ debug, cần xem nội dung trước khi chia sẻ. Server chỉ bind loopback, kiểm tra Host/Origin và token phiên; đây là test harness cục bộ, không phải dịch vụ mạng dùng chung.

## Chế độ mô phỏng

Chọn **Simulated reader** trước Connect. Tag có EPC `E20034120123456789000001`, TID `E280116060000205DEADBEEF`. Backend vẫn đi qua codec/parser/dispatcher thật của SDK. **Inject once** áp dụng phản hồi kế tiếp: F9, FC/04, 13 hoặc không phản hồi.

Bộ mô phỏng hỗ trợ config, inventory, buffer và memory phục vụ kiểm tra GUI/lifecycle. Lệnh chưa mô hình hóa trả lỗi native; không giả việc đã kiểm thử chip hay firmware. Không dùng tỷ lệ đọc/timing của simulator để đánh giá RF. Xem **Support & evidence** để biết chức năng C# còn thiếu.

## Kiểm tra phần mềm

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_demo_app.py tests/integration/test_demo_live.py tests/integration/test_observability.py -q
node --test tests/browser/demo_client.test.cjs
```

GUI nằm ngoài wheel SDK, có trong source tree và sdist. Core giữ khả năng chạy CPython/Pyodide; HTTP/threads/serial là phần app thử nghiệm CPython.
