# Đối chiếu SDK, NATION và demo ZK V6.8

Ngày đánh giá: 2026-10-09. Bản NATION tham chiếu: `compat/nation/nrn.py`, commit `d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b`. Đối chiếu ZK với manual V2.25, source C# V6.8 tại thư mục người dùng cung cấp và các ảnh màn hình. Không coi danh sách DllImport là bằng chứng đủ để suy ra opcode/byte layout.

## Kết luận

SDK có cấu trúc host protocol tương đương về các lớp chức năng nền tảng: transport, codec, response/error, lifecycle, inventory, config, tag operation, log và công cụ kiểm thử. **Chưa thể khẳng định tương đương hoàn toàn NATION hoặc đủ mọi nút của demo ZK C# V6.8**, cũng chưa đủ chứng cứ nghiệm thu phần cứng toàn bộ.

NATION là protocol và firmware khác. API async ZK không thay trực tiếp `NRNReader` blocking/threading. Số phương thức lớn hơn không chứng minh feature parity hoặc hiệu năng RF tương đương. [Adapter và RF mapping](nation_comparison.md) còn những mục unverified/unsupported được ghi rõ.

## Khả năng gửi lệnh, nhận phản hồi, quản lý trạng thái

| Yêu cầu | SDK hiện tại |
|---|---|
| Send/receive frame | Native ZK CRC, frame parser, một RX dispatcher; không có RX riêng trong GUI |
| Ghép request/response | Pending trước TX, địa chỉ/opcode, exchange ID trong trace; late/wrong response có diagnostics/fault |
| Success / device error | CommandResult giữ status native, raw payload, nested tag error; không thu gọn mọi lỗi thành bool |
| Timeout / mất kết nối | UNKNOWN nếu đã TX mà chưa xác nhận; fault chặn thao tác tiếp theo tới khi phục hồi |
| Inventory nhiều frame | InventoryOutcome giữ report nhận được, reason, complete, dropped_count, statistics, partial |
| ACK và đọc lại | Phân biệt acknowledged/transmitted/read_back_verified; nhiều bước giữ steps |
| Start/stop | Host lifecycle và mode riêng; stop93 không tự có ACK; Scenario dùng stop51/restore |
| Log tập trung | Mới bổ sung TraceEvent/on_event, logger zk_rfid.trace; app JSONL xoay vòng, export, lọc, loss/error counters |
| Theo dõi thiết bị | Kết nối, pending, host state, cached mode, parser diagnostics; không tự suy RF state từ COM đang mở |
| GUI | Mới bổ sung local HTML trong tests/demo_app; 74/74 public reader method có đường gọi |
| Kiểm chứng thực tế | Unit/integration/CPython/Pyodide; người dùng báo 3 hardware tests pass qua ảnh; chưa nghiệm thu mọi chức năng |

Bản trước đã có typed result/errors và dispatcher nhưng chưa có trace tập trung gắn request–frame–result cho GUI. Đợt này bổ sung khả năng quan sát đó; không sửa baseline `nrn.py`.

Ví dụ diễn giải khi bấm Send:

| Tình huống | Dữ liệu thực cần xem | Diễn giải |
|---|---|---|
| Setter nhận status 0x00, không payload | outcome=success, confirmation=acknowledged | Module xác nhận lệnh; chưa chứng minh persistence qua power cycle |
| Getter nhận 0x00 và payload đúng layout | data đã giải mã + raw_data | Thành công theo phản hồi native |
| Native 0xF9 | failure, status=249, diagnostics=command_failed | Thiết bị từ chối/thực thi lỗi |
| Native 0xFC, payload 04 | failure, status=252, tag_error=4 | Lỗi trả từ tag được giữ riêng; cần đọc theo contract tag |
| Native 0x13 | partial, persistence_failed | Không báo thành công hoàn toàn; việc lưu chưa xác nhận |
| Hết deadline sau TX, không phản hồi | unknown, status=null, confirmation=transmitted | Không biết lệnh đã tác động hay chưa; không tự retry mutation |
| ValidationError trước TX | failure, loại lỗi + mô tả; không frame TX mới | Sai tham số cục bộ, chưa phải mã lỗi module |
| Inventory 0x01 / 0x03 / 0x02 / 0x04 / 0x26 | complete/more_frames/device-timeout/buffer-full/statistics | Diễn giải theo opcode, không dùng quy tắc “khác 00 là lỗi” |
| Stop Answer 0x93 | TX93 và kết thúc phản hồi inventory gốc | Không chờ một ACK93 không tồn tại trong protocol |
| Write rồi đọc lại khớp | read_back_verified + steps | Đã xác minh dữ liệu đọc lại với target/độ dài đã chọn |

Event timestamp monotonic dùng thứ tự/duration của host; JSONL thêm wall clock. Raw RX giữ cả chunk lỗi; event frame chỉ sau parser kiểm tra. Observer đồng bộ phải ngắn, không I/O chặn; exception observer được đếm và không phá RX. Logger mặc định tuân theo cấu hình logging của ứng dụng, không tự cài handler.

## Các nhóm trong ảnh demo hãng

| Demo C# / chức năng | API Python + GUI | Giới hạn |
|---|---|---|
| RS232, info, serial, address, baud, max inventory time | Có | Cổng/model/firmware do người dùng chọn |
| Region min/max channel, global/per-port power, write power/retry, DRM | Có | Native ZK band/profile, không map NATION tự động |
| Antenna enable/check, temperature, return loss | Có | Getter đầy đủ 16-port còn hạn chế; module 1-port dùng đường đã định nghĩa |
| Beep, GPIO, indicator pulse | Có | Không đồng nhất reader indicator với LED chip tag hay notification OUT1..4 |
| Relay, notification pulse OUT1..4, Range Control | Chưa có API tương ứng | Cần chốt native wire contract, không gọi DLL qua UI |
| Custom frequency start/count/spacing, Ex10 version query | Chưa có API tương ứng | Region/channel và reader firmware hiện tại không thay cho hai chức năng này |
| Real-time mask/TID/Q/session/filter/pause/mode | Có | Một số cấu trúc qua JSON; Trigger phụ thuộc wiring/firmware |
| Answer EPC/TID/FastID/Mix, phase, Q/session/target, antenna | Có | FastID/phase/Mix có điều kiện; Mix >31 word chưa verified |
| Scenario start/stop, query/TID/mask/3 custom profiles | Có | Snapshot/restore cấu hình; restore16port còn hạn chế |
| Buffer length/read/count/clear/inventory | Có | Buffer record16port cần capability xác nhận |
| Read/Write/ExtRead/ExtWrite, EPC/PC/password, BlockWrite/Erase | Có | Normal/extended dùng extended_format hoặc auto; read-back có target |
| Lock/Kill Gen2 cơ bản | Có | GUI xác nhận thao tác và target; không tự test destructive trên module |
| MarginRead, U9 batch lock, LED tag | Chưa có | Không được coi lock/indicator thường là chức năng tương đương |
| NXP Privacy/EAS, Monza QT, EM4325 | Unsupported | Ngoài contract tag hiện tại |
| TCP/IP/network module configuration, ISO18000-6B | Ngoài phạm vi | SDK Gen2/6C, transport inject + serial; chưa có TCP GUI |

CFG25/29 có getter raw và setter gated theo dialect đã xác minh; không tích checkbox “confirmed” chỉ để vượt validation. Nguồn [errata](protocol/errata.md), [ma trận hỗ trợ](supported_devices.md), [symbols sinh từ source](functions_implemented.md).

## Nghiệm thu cần làm với module một port

Ảnh người dùng cung cấp cho thấy `test_info_serial_and_power`, `test_region_and_profile`, `test_answer_round` PASS trên COM13/115200. Đây là bằng chứng do người dùng báo; agent chưa thu raw trace phần cứng trong đợt GUI. Test Answer pass không tự chứng minh đã đọc một tag nếu assertion chỉ kiểm tra kiểu/kết thúc hợp lệ.

Dùng [hướng dẫn GUI](../tests/demo_app/README.md) để lưu log model/firmware thực tế cho từng API cần nghiệm thu. Trước kết luận đầy đủ cần kiểm tra read-back đúng target, persistence sau power cycle, error/no-tag/timeout, stop khi đang stream, real-time/trigger, buffer và các capability có điều kiện. Đánh giá RF cần tag/antenna/môi trường/duration/ground truth riêng, theo [inventory benchmark](inventory_benchmark.md).
