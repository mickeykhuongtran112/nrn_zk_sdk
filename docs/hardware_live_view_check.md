# Kiểm tra live view trên module thật — 2026-10-09

## Nguyên nhân và chuyển phiên chạy

Server cũ tại127.0.0.1:8765, PID9964 khởi động17:21:55, vẫn dùng modulePython trước khi bổ sung live và quy đổi đo lường. Bootstrap không có api_revision, `/api/live` trả404, snapshot trả `rssi_dbm=null`. Disconnect/Connect chỉ đóng/mở serial trong cùng tiến trình, không nạp lại Python. Frontend mới phải dùng snapshot750ms nên bảng cập nhật theo đợt.

Đã lưu snapshot/CSV cũ vào `local_data/server_upgrade/before_restart_*`. Khi kiểm tra, inventory đã idle. Disconnect job67 trảsuccess và connected=false. Windows từ chối Stop-Process với Access denied; không cố vượt quyền. Bản mới được chạy tại **http://127.0.0.1:8766**, PID20096, bootstrap api_revision2, features.live_tags=true. Server8765 vẫn tồn tại nhưng đã disconnectCOM13.

## Phiên đọc kiểm chứng

- Nguồn: module thật, COM13,115200bps,1port; không bật simulator.
- start_inventory: Scenario, EPC, antenna1, Q4, session0, phase=true; cấu hình qua form demo. Scenario dùng report0xEE.
- UI hiển thị cả raw và dBm theo `raw - 135`, ví dụ96→−39,85→−50,104→−31; phase begin/end có độ và raw trong metadata.
- Một chuỗi quan sát DOM thực tế: count của tag đầu775,776,776,777,778,779; tổng tương ứng7490,7501,7501,7511,7522,7533. Không tạo thêm count để làm animation.
- Cửa sổ đo HTTP khoảng3giây:74gói cập nhật có dòng thay đổi, khoảng cách trung vị40,21ms, lớn nhất56,72ms; tổng tăng3162→3864. Đây là nhịp dữ liệu tới clientHTTP, không phải phép đo FPS/trễ RF end-to-end.
- Trong cửa sổ đó: queueSDK dropped0/queued0, CRCfailures0, discardedbytes0, parseroverflows0, unexpectedframes0.
- Kết thúc phiên:7.594reports,14ID/antenna entries; stop_inventory job3 trảsuccess, complete=true, dropped_count0. Lifecycleidle, session=null. Giữ kết nối serial cho người dùng tiếp tục, RF phiên kiểm tra đãStop.

Chứng cứ cục bộ (không đóng gói/phân phối):

- `local_data/demo_logs/20261009-183650-980500.jsonl`: traceSDK RX/TX/frame/tag/state/job; có thể xoay vòng nếu tiếp tục dùng app.
- `local_data/server_upgrade/live_hardware_probe.json`: điểm thời gian/góiHTTP và diagnostic trong cửa sổ đo.
- `local_data/server_upgrade/after_restart_snapshot.json`, `after_restart_tags.csv`: kết quả sauStop.
- `artifacts/zk-demo-hardware-live-dbm.jpg`: ảnh bảng thật, cột dBm/phase và trạng tháiLive.

Chưa đo hiệu chuẩnRSSI tuyệt đối, hiệu năngRF tổng thể, mọifirmware/mode hoặc độ trễ từchip tới màn hình. MappingdBm vẫn là quy ước do người dùng yêu cầu.

## Đối chiếu frontend Nextwaves

Đọc [trang reader](https://app.nextwaves.com/reader) và [bundle frontend công khai](https://app.nextwaves.com/_next/static/chunks/0dv97g72me5ox.js) ngày2026-10-09: đường đọc local dùngWebSerial, mở readable.getReader(); xử lý tag tăng count trong map, gom thay đổi tag và cập nhật stateUI theo interval200ms. Bundle có cả chức năng remoteWebSocket riêng; không nhầm kênh đó với đường đọc serial local. BảnZK/Chainway trong bundle còn có vòng gửiinventory95ms, khác lifecycleScenario0x50/0xEE của SDK này, nên không sao chép timer gửi lệnh đó.

DemoSDK dùngPython giữ một RXowner, đưa cumulative tag quaNDJSONlive riêng, coalesce33ms rồi vẽrequestAnimationFrame. Đo được khoảng40ms giữa cập nhậtHTTP trong phiên trên. Web không phải giới hạn của trường hợp lỗi: server cũ thiếu endpoint khiến giao diện quay vềsnapshot750ms. Hai bên đều có thể gom nhiều report trong một lần vẽ; số đếm hiển thị vẫn phải phản ánh dữ liệu đã nhận.
