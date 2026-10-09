# Errata và giới hạn có chủ đích
Nguồn gốc: UHF RFID Reader Series User Manual V2.25,106trang PDF; SHA256 5f4675a61bcab11a214422c70d3aa24e2ace3d7ac10ab888e958b21636d5d0be. Demo Ex10 Module SDK V6.8: ParamSetting.cs và RWDev.cs. Không đóng gói manual/DLL.

Số trang dưới đây là trang in; PDF thường cộng4. Chưa chạy hardware mới trong project; evidence demo/DLL loopback không thay RF trace.

| Điểm | Xử lý trong SDK |
|---|---|
| Password tổng quan trang12 nhầm độ dài | Mỗi Kill/Access password32bit theo command chi tiết |
| Info21 example Len mâu thuẫn field table | Decode đúng12data byte, reject length khác |
| Power94 response ghi51, trang97 | Match94; historical source project có DLL/reader evidence94. Không nhận51 vì đụng fast-stop |
| CFG25/29 trang99/101:10byte ở summary,6/5 ở detail | Getter giữ raw; setter chỉ khi caller chọn cfg25_length=6/cfg29_length=5. Chưa xác minh dialect trên module |
| WriteEPC04 trang21–22 ENum<15 vs WEPC31word | Giới hạn04 ở1..14word; targeted03 qua PC hỗ trợ tối đa31wordEPC |
| Extended16 tiêu đề gọi reading | Theo frame/content writing, không theo tiêu đề |
| 50/51 trùng opcode6B | Chỉ Ex10 Gen2 context; toàn bộ6B ngoài scope |
| Stop93 trang98 | Không ACK93; chỉ ngắt01, theo completion01 |
| CFG9 session/phase demo vượt bảng manual | Demo phasebit4; session128/252/253/254 được mã hóa explicit. Không tự map sang Gen2 session chuẩn |
| Scan CFG7 defaultdwell0 ngoài range2..255 | Cho0 hoặc2..255; từ chối1 |
| Mix ReadLen120word vs Len low6bit/phasebit6 | Cho<=31word; đọc32..120word dùng read_memory |
| Phase scale và folding trong demo không thống nhất | Giữ raw4byte + begin/endBE16; độ/radian theo nhánh hiển thị thông thường Form1.cs: raw×0.087mod180. Metadata ghi rõ convention; helper wrap=False cho giá trị chưa fold. Không scaleNATION, không gọi là phase tuyệt đối calibrated; xem [chi tiết](../phase_and_live_view.md) |
| GPIO số pin/bit mô tả không nhất quán | Hai outputbit0/1; getter inputbit0, outputsbit4/5; cần kiểm tra pin thực |
| Buffer16port Ant1/2byte mâu thuẫn | Yêu cầu buffer_antenna_bytes caller xác nhận |
| Reader-info chỉ1byte antenna mask | Getter và Scenario auto-restore16port không được công bố hỗ trợ |
| Region21/29 đoạn tần số gián đoạn mơ hồ | Set/getnative vẫn có; helper channel_frequency_khz từ chối quy đổi |
| Buffer70 "length" | Là maxEPC/TID16 hoặc62byte, không phải KBcapacity. Manual nêu tối đa528/160tag tương ứng |
| Return-loss91 chỉ Ant0..3 | Diagnostic giới hạn4port dù reader có thể nhiều port |

Mỗi lần gỡ giới hạn phải bổ sung model, firmware, request/response raw, điều kiện tag/RF và regression vector. Không âm thầm fallback layout sau một command đã TX.
