# NATION / synthetic

Vector chủ động tạo cho kiểm thử. Hiện chưa có vector trong thư mục này.

Mỗi case cần: nguồn/revision hoặc commit, model/firmware khi có, TX/RX, expected result, đơn vị/endian và điều kiện áp dụng. Case stream cần chunk boundary và timing; case lỗi cần mô tả lỗi được đưa vào.

Với capture thật, thêm baud, anten/RF config, chip tag, thời điểm và thao tác. Dữ liệu private chưa chọn lọc để tại local_data. Không đổi nhãn documented/synthetic thành captured khi chưa đo trên thiết bị.
