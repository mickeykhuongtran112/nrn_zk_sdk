# Phase, RSSI và cập nhật trực tiếp

## Nguyên nhân giao diện cập nhật theo từng đợt

Bản trước gọi snapshot và log cùng một Promise.all, sau đó chờ 600 ms. Việc tải/vẽ log ảnh hưởng trực tiếp nhịp bảng tag; mỗi lần lại dựng toàn bộ bảng. Ngoài ra, InventorySession Answer chỉ đưa report vào iterator sau khi collect_answer kết thúc một vòng.

Bản sửa dùng HTTP stream NDJSON riêng tại /api/live (cùng kiểm tra Host/Origin/token), đẩy thay đổi của các dòng với bộ đếm cộng dồn. Coalesce khoảng 33 ms khi có dữ liệu; khi idle gửi heartbeat 1 giây. Browser vẽ bằng requestAnimationFrame và giữ nguyên node của dòng. Snapshot trạng thái và log chạy riêng. Pause view dừng tải/vẽ log trên browser, không dừng nhận tag hoặc ghi file.

Mỗi browser có cursor riêng. Client chậm không tạo hàng đợi report vô hạn: server giữ trạng thái hiện tại của tối đa 1.000 dòng hiển thị đầu tiên; khi kết nối lại gửi reset và số đếm hiện tại. Kho đầy đủ để export vẫn giữ tối đa 5.000 ID/antenna entries. Tràn kho này được đếm riêng; không bỏ việc ghi tag vào audit log. Queue SDK, parser loss và disk log drop có chỉ báo riêng.

Answer session nay đưa report đã decode vào iterator ngay từ frame trung gian (status03); kết quả cuối vòng vẫn giữ đầy đủ báo cáo/trạng thái. Không nhân đôi report lúc vòng kết thúc. Mix chỉ có thể đưa ra report đã ghép EPC/memory; EPC thiếu memory được flush khi đủ căn cứ hoặc kết thúc vòng. API inventory_once vẫn trả một InventoryOutcome sau khi hoàn tất vòng.

30 updates/s là giới hạn mục tiêu của *hiển thị*, không giới hạn đọc RF. Khi nhiều report đến giữa hai lần vẽ, bộ đếm có thể tăng nhiều đơn vị. Không nội suy hoặc tạo giả các lần đọc 1, 2, 3. Trình duyệt ở background có thể giảm nhịp vẽ; quay lại sẽ thấy số cộng dồn hiện tại. Đây không phải bảo đảm latency thời gian thực.

Log người dùng cung cấp 20261009-172155-266500.jsonl (và các bản xoay vòng) ghi Answer/FastID ở 17:30:20, Scenario có phase ở 17:32:22 và 17:33:00. Ảnh opcode01 lúc17:30 là Answer. Các report Scenario đã nhận ở host cách nhau cỡ mili giây; nhịp UI600ms không đại diện nhịp RX. Log giữ lại không đủ để chứng minh không mất report trong toàn phiên hoặc đánh giá hiệu năng RF.

## Quy ước phase có nguồn

Nguồn cục bộ của người dùng, không phân phối lại trong SDK:

- UHF RFID Reader Series User Manual V2.25, trang in17 / PDF21: extension phase4byte + frequency3byte; trang in48 / PDF52: phase gồm 2byte begin + 2byte end.
- Ex10 Module SDK V6.8, english/Demo/c#/UHFReader288Demo_eng V6.8/RWDev.cs, khoảng dòng1243–1265: decode hai word big-endian; RSSI chuyển sang byte unsigned.
- Form1.cs, dòng1254–1255 và2936–2937: phase_begin/end * 0.087f % 180; hiển thị3chữ số thập phân. Một nhánh thêm dòng FastID ở1314–1315 bỏ modulo, còn nhánh cập nhật dùng modulo. SDK chọn convention hiển thị thông thường và ghi rõ tên, không suy diễn scale từ NATION.

TagReport khi có extension giữ:
- phase_raw: 4byte gốc.
- phase_begin_raw, phase_end_raw: integer unsigned16bit.
- phase_begin_degrees, phase_end_degrees: (raw × 0.087) % 180, float.
- phase_begin_radians, phase_end_radians: degrees × pi / 180, float.
- phase_conversion: ex10_v6_8_demo_0.087deg_mod180.

Không ép góc thành integer vì sẽ mất độ phân giải. Ví dụ 018F018D tách thành399 và397, tương ứng34.713° và34.539°. Giá trị không có trong frame vẫn là None; phase0 là giá trị hợp lệ. Field cũ phase_radians (số ít) vẫn None để không gán tùy ý phase begin hay end.

```python
from zk_rfid import phase_to_degrees, phase_to_radians

phase_to_degrees(0x018F)              # 34.713
phase_to_radians(0x018F)              # approximately 0.605856
phase_to_degrees(0x0E8F)              # 144.249, folded
phase_to_degrees(0x0E8F, wrap=False)  # 324.249, scaled without folding
```

Đây là chuyển đổi theo demo hãng, không phải chứng nhận đo phase tuyệt đối đã hiệu chuẩn. Không tự thay0.087 bằng360/4096. Dữ liệu đã modulo180 mất thông tin nhánh; ứng dụng xử lý phase/đa đường/theo dõi chuyển động nên lưu raw và frequency_khz, kiểm chứng quy ước trên đúng firmware và điều kiện RF.

## RSSI

Manual và demo trên xác nhận1byte unsigned. Theo yêu cầu người dùng ngày2026-10-09, SDK bổ sung ánh xạ tuyến tính **raw60→−75dBm, raw110→−25dBm**:

`rssi_dbm = rssi_raw - 135`

| Raw | dBm quy đổi |
|---|---|
| 60 | -75 |
| 85 | -50 |
| 100 | -35 |
| 110 | -25 |

Helper public `rssi_to_dbm(raw)` nhận uint8 và trả float. Tất cả decoder Answer/FastID/TID/Mix/Scenario/Real-time/Buffer áp dụng cùng công thức. Không clamp ngoài60..110: ví dụ59→−76,111→−24; metadata đánh dấu ngoại suy. Đây là mapping do người dùng đặt, chưa phải hiệu chuẩn RF tuyệt đối hoặc công thức do hãng công bố; không dùng công thức NATION.

TagReport giữ `rssi_raw`, thêm giá trị `rssi_dbm`, nguồn `rssi_source="user_linear_raw_minus_135"` và `rssi_in_calibration_range` (True khi60≤raw≤110). Report không có RSSI giữ các field None. Khởi tạo TagReport thủ công không tự suy ra các field đo; helper dùng khi ứng dụng muốn tự quy đổi. Adapter NATION cũng chuyển tiếp các field có đơn vị/nguồn này, không gán alias RSSI native của NATION.

GUI có hai cột RSSI RAW và RSSI · dBm, hiển thị dấu* nếu ngoại suy. CSV/JSONL chứa cả giá trị và metadata; log wire giữ nguyên bytes. Cần restart Python server và Ctrl+F5 để sử dụng code mới.

## Dùng bản sửa

Nếu log có TAG nhưng bảng trống và báo disconnected, kiểm tra phiên bản server trước. Ngày2026-10-09 xác minh server cổng8765 vẫn trả snapshot chứa25dòng/8.375reports nhưng `/api/live` trảHTTP404: tiến trình Python cũ đang phục vụ fileJS mới từ ổ đĩa. F5 không nạp lại modulePython.

GUI hiện lấy bảng từ snapshot khi luồnglive chưa sẵn sàng hoặc bị ngắt. Chế độ dự phòng báo rõ Snapshot, chu kỳ750ms cộng thời gianHTTP; không tạo lần đọc giả và không gửi thêm lệnhRF. HTTP404/405/501 dừng retry endpoint không hỗ trợ và hướng dẫn restart. Lỗi mạng tạm thời vẫn retrylive; khi có lại sẽ lấy số đếm hiện tại. Snapshot đến muộn không được ghi đè dữ liệu live mới. Chọn tag được giữ qua các lần cập nhật, xóa khi clear/đổi thế hệ hoặc dòng biến mất.

Bootstrap bổ sung `api_revision=2`, `features.live_tags`; cảnh báo khi UI và API khác phiên bản. Server mới giữ HTML/JS/CSS trong bộ nhớ khi khởi động để tránh trộn bản mới trên disk với Python đã nạp. Vì vậy thay đổi cả frontend lẫn Python đều cần restart server rồi tải lại trang. Dữ liệu dBm/phase mà server cũ chưa trả vẫn hiển thị `—`, không tính riêng trên frontend làm lệch CSV/SDK.

Stop inventory → Disconnect trên app đang chạy, Ctrl+C terminal để tắt server cũ. Khởi động lại:
```powershell
.\.venv\Scripts\python.exe -m tests.demo_app --port COM13 --baud 115200 --ports 1
```
Mở http://127.0.0.1:8765 và Ctrl+F5. Chọn start_inventory, mode=scenario, data=epc, antenna=1, bật Phase. Kiểm tra Active session: Scenario · 0x50 / 0xEE; chọn Phase unit để đổi degrees/radians/raw integer. CSV và JSON giữ cả raw lẫn đơn vị quy đổi.

## Kiểm chứng phần mềm

Regression tests bao gồm: đổi phase qua các layout Answer/FastID/TID/Mix/Scenario, vắng phase, wrap180, uint16 bounds, RSSI>127 không bị signed; Answer trả report trước terminal frame, queue overflow vẫn Stop được; slow browser20.000reports giữ đúng tổng và1dòng; nhiều client, reset/reconnect và HTTP stream có token.

Client regression: `node --test tests/browser/demo_client.test.cjs` kiểm tra server cũ404, fallback/reconnect, snapshot đến muộn, clear/new generation và legacyfirst_seen. HTTP test xác nhận asset không đổi giữa phiên dù file trên disk thay đổi; chỉ instance server mới dùng asset mới.

Browser simulator gửi một tag mỗi150ms: quan sát được bộ đếm73→74→75→…→81; Pause log vẫn đọc tiếp. Thử độ/radian/integer cho raw256/512 lần lượt22.272°/44.544°,0.388720/0.777439rad,256/512. Đây là kiểm tra phần mềm, không mở COM13 hoặc đo lại module thật.
