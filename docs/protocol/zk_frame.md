# Wire framing ZK
Nguồn: UHF RFID Reader Series User Manual V2.25; phạm vi Gen2/6C và reader commands.

TX: Len | Adr | Cmd | Data... | CRC_L | CRC_H
RX: Len | Adr | Cmd | Status | Data... | CRC_L | CRC_H

Len không tính chính byteLen, uint8; frame tối đa256byte, TXdata<=251, RXdata<=250. Không có sync header0x5A. Địa chỉFF dùng broadcast trên kết nối point-to-point; response cung cấp địa chỉ reader. Không hỗ trợ nhiều response reader trên bus đồng thời.

CRC reflected polynomial0x8408, init0xFFFF, xorout0; tính từLen đến hếtData, append low byte trước. Check "123456789"=0x6F91; CRC của toàn frame hợp lệ=0.

Golden TX reader-info broadcast:04 FF21 1995 (viết liền:04ff211995). Tám vectors độc lập được nhập từ historical vendor-DLL loopback, metadata ở fixtures/zk/documented/frames.json. Đây không phải capture RF mới.

FrameParser nhận bytes chunk tùy ý, phân tích nhiều frame, kiểm CRC và resync khi lỗi; không suy ra khoảng cách byte từ timestamp chunk OS. Diagnostics đếm frames/discarded/CRC/overflow. Noise có thể phục hồi frame nhưng làm inventory partial vì completeness không còn bảo đảm.

Dispatcher đăng ký pending trướcTX, serialize ordinary commands, một RX task. Match Cmd+address; special command00/statusFE là error context. EE là notification;93 không ACK riêng. Response trễ/unexpected response làm connection fault để không gán nhầm transaction sau.

Timeout monotonic bao gồm chờ operation lock và toàn chuỗi nhiều bước. Short write tiếp tục phần bytes chưa được transport nhận; không gửi lại command đã hoàn thành. EOF=b""; serial polling timeout được transport hấp thụ, không giảEOF. Sau exchange không xác định, chỉ recover khi caller đã thiết lập boundary sạch.
