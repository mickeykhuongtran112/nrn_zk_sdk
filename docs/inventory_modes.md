# Inventory: mode và loại dữ liệu
Đã triển khai phần mềm theo V2.25 và demo V6.8; chưa xác minh RF trên module trong project.

| Mode | Start / dữ liệu / stop | API và cấu hình |
|---|---|---|
| Answer từng lượt | 01, hoặc 19 Mix; nhiều response; status kết thúc | inventory_once(InventoryConfig(...)) |
| Answer liên tục | Host lặp các round; 93 ngắt riêng 01, không có ACK93 | start_inventory(InventoryMode.ANSWER) |
| Scenario Ex10 | 50 / EE / 51; start ACK không phải completion | start_inventory(InventoryMode.SCENARIO) |
| Real-time | 75 cấu hình; 76=1 chạy, 76=0 dừng; EE report | set_real_time_config rồi start_inventory(REAL_TIME) |
| Trigger | 76=2, cùng config75; input trigger do reader xử lý | start_inventory(REAL_TIME, trigger=True) |
| Buffered | 18 ghi buffer; 72 lấy các frame; 74 count,73 clear | inventory_to_buffer, read_buffer |
| Single / EPC match | 0F / 1A | inventory_single, inventory_matching_epc |

## Loại dữ liệu

- EPC: report EPC; không tự tạo PC hoặc TID.
- TID: Answer dùng AdrTID/LenTID; Scenario dùng CFG10, LenTID=1..15. Report là TID-only.
- FastID: bit5 Q của 01; khi tag hỗ trợ, bit7 Len báo EPC ghép TID96bit. Tag không hỗ trợ có thể chỉ trả EPC; thiếu TID không được bịa.
- Mix: 19, EPC và memory là hai record liên tiếp có sequence/antenna. Decoder ghép có kiểm tra; thiếu memory vẫn giữ EPC và đánh dấu partial. Giới hạn hiện tại 31 word bởi errata Len/phase.
- Phase: Answer giữ raw4byte; Mix/Scenario có begin/end raw16bit theo demo và frequency24bit kHz. Không quy đổi radian.

Scenario không có contract FastID/Mix đã xác minh. Real-time dùng config75 đã lưu: q/session/mask/TID/filter khác CFG9/10/11. SDK kiểm tra data kind với getter77; từ chối phase/statistics flags không được hỗ trợ. Các field khác trong InventoryConfig không thay config75.

## Completion và điều phối

03 là còn frame;01 hoàn tất;02 device timeout;04 buffer full. Nếu bật statistics, tiếp tục đợi26 sau terminal tag frame. FB là không có tag. Complete chỉ nói về giao dịch protocol; không phải xác nhận tất cả physical tag đã được đọc.

Một RX task duy nhất. Session có queue hữu hạn và consumer async iterator. QueueOverflow ghi dropped_count; không drop âm thầm. Heartbeat là event riêng, không tính là tag. Callback của adapter chạy trong consumer task.

Scenario snapshot CFG9/10/11, ghi volatile và đọc lại trước50; tạm chọn một antenna theo config. Sau51 ACK, khôi phục snapshot và đọc lại. Getter antenna16port chưa đủ bằng chứng, nên orchestration tự khôi phục giới hạn <=8port. Lỗi cleanup được báo, không trả success giả.

93 chỉ gửi khi01 đang pending; không tạo pending93. Mix19 chờ round kết thúc. Real-time stop bằng76=0, có side effect lưu mode. EE đến sau stop ACK làm connection unknown để tránh lẫn report với phiên kế tiếp.

Dùng async context của session hoặc finally: await session.stop(). Cancel host không tương đương stop reader. Đặt scan time hữu hạn; scan=0 yêu cầu caller quản lý stop/deadline. Default deadline tăng theo scan_time_100ms + 250ms margin, timeout explicit là toàn bộ ngân sách kể cả chờ lock.
