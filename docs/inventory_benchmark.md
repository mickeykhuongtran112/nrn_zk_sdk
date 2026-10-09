# Inventory benchmark — dự kiến

Chưa có kết quả benchmark. Tài liệu này định nghĩa phép thử, không công bố mode nào luôn nhanh/đủ hơn.

## Điều kiện phải ghi

Model/firmware, mode, RF profile, region/frequency, power, anten/thứ tự/dwell, Q/session/target, TagFocus/FastID, kiểu dữ liệu/count, baud, filter/report policy, chip tag, vị trí/hướng/vật liệu và số tag trong vùng.

So Answer/Scenario ở điều kiện tương đương. Tách giới hạn RF, UART, host scheduling, parser và tốc độ cập nhật giao diện của công cụ đo. Report/s không đồng nghĩa unique tags/s; EPC trùng không được dùng để đếm chắc chắn số tag vật lý.

## Metrics

- Tỷ lệ ID đúng tìm được trong cửa sổ thời gian so với tập ground truth.
- Stray tags/false positives ngoài vùng.
- First-read latency, thời gian đạt mục tiêu và thời gian tag cuối cùng.
- EPC+TID completeness nếu cả hai bắt buộc; EPC-only thành công chưa đủ.
- Độ lặp lại trên nhiều lần thử và nhiều cách xếp/hướng tag.
- Queue depth, lost/delayed reports, CPU/memory và throughput UART.

Không có tag mới trong một khoảng chỉ là stop heuristic. Expected count không thay thế đối chiếu đúng ID. Trạng thái inventoried của tag giữa hai lượt phải được quản lý để tránh bias.

## Ca ứng dụng để thử

| Ca | Phương án xuất phát để đo |
|---|---|
| Kiểm kho đông tag | Scenario EPC, thử session/target giảm đọc lặp |
| Bàn tính tiền | Phiên giới hạn, kiểm soát stray reads và hàng thêm/bớt |
| Chấm công đi qua | Scenario; latency, che bởi cơ thể, duplicate event và vùng đọc |
| Thùng đọc | Thu thập, đổi anten/profile khi cần, đối chiếu danh sách |
| Tunnel/băng tải | Cửa sổ sensor/encoder; T khả dụng xấp xỉ chiều dài vùng hiệu dụng/tốc độ |

Đây là ca benchmark, không đưa logic hóa đơn/chấm công hoặc phân kiện vào core SDK. Các mã preset của reader khác không được sao chép sang ZK chỉ vì tên tương tự.
