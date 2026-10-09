# Tag reports và measurements
Nguồn: V2.25 inventory tables, Ex10 V6.8 RWDev.cs/ParamSetting.cs. Parser phụ thuộc context command/mode/data; không dùng một decoder chung đoán EPC/TID.

| Report | Layout được xử lý |
|---|---|
| Answer01/0F/1A | Ant + Num + [LenFlags + ID + RSSI + optional7byte phase/frequency] |
| FastID01 | Len.bit7; ID gồm EPC và12byteTID ở cuối |
| TID01 | ID là TID theo request, không tự coi là EPC |
| Mix19 | Ant + Num + record sequence/type; ghép EPC/memory cùng antenna và seq kế tiếp, wrap127 |
| ScenarioEE | Ant + LenFlags + EPC hoặcTID + RSSI + optionalphase/frequency |
| Real-timeEE | Native basic report; dùng saved75 để biết EPC/TID |
| HeartbeatEE/status28 | Decoder riêng, không tạo TagReport |
| Statistics/status26 | Ant + rateBE16 + totalBE32 |
| Buffer72 | Num + [Ant mask + Len + ID + RSSI + read count]; data kind do caller biết từ round trước |

Len thấp6bit là độ dài ID bytes; bit6 chỉ phase extension, bit7 FastID khi command hỗ trợ. Phase4byte và frequencyBE24kHz là phần bổ sung. Answer/FastID/TID/Mix/Scenario tách begin/end BE16 theo demo. SDK giữ raw và thêm độ/radian theo `(raw * 0.087) % 180`, có metadata `phase_conversion`; xem [nguồn và giới hạn quy đổi](../phase_and_live_view.md). RSSI giữ unsigned raw, thêm `rssi_dbm=raw-135` theo mapping người dùng (60→−75,110→−25); metadata ghi rõ nguồn và giá trị có nằm trong dải60..110 hay không.

TagReport giữ raw, epc/tid/memory_data, bank/word_address theo context, antenna/antenna_mask, timestamp_source. received_at là thời điểm host monotonic nhận frame, không phải timestamp RF. Field không có dùngNone. Không tự tạo PC từ EPC length.

Mix thiếu memory hoặc orphan memory được ghi diagnostics; EPC hợp lệ vẫn giữ. Queue overflow, malformed payload, parser byte loss và timeout đều làm outcome phản ánh thiếu dữ liệu. Unique_count theo ID được report, không thể phân biệt physical tags có cùng EPC.

Không hỗ trợ Mix>31word đến khi xác minh extension của length/phase. Buffer16port cần chọn antenna width dựa trên capture firmware, không đoán từ tên module.
