# Ma trận hỗ trợ

0.1.0.dev1,2026-10-09. **Chưa có model/firmware/tag hardware verified trong project này.**

ZK-7180M/ZK-7182M theo plan dùng manual V2.25/demo Ex10 V6.8. ReaderCapabilities khai báo layout, không phải autodetect; caller chọn1/4/8/16port theo module thực. Default1 là cấu hình bảo thủ. Info giữ model_code/firmware bytes, không tự gán model.

| Chức năng | Python | Điều kiện |
|---|---|---|
| Frame/CRC/parser/dispatcher | Implemented + tested | Một reader, timeout sau TX khóa connection |
| Info/serial/address/baud/interface | Implemented | Baud transport phải hỗ trợ đổi; interface cần power cycle |
| Power/write power/retries | Implemented |0..30dBm, số giá trị đúng port |
| Antenna mux/check | Set1/4/8/16 implemented | Get full mask chỉ tới8port |
| Answer EPC/TID/FastID/phase/statistics | Implemented | FastID cần tag hỗ trợ, measurement không calibrated |
| Single/match EPC/buffer inventory | Implemented | Match1..196bit,offset+len<=496 |
| Mix EPC+memory | Implemented tới31word | Len bit6 mâu thuẫn >62byte; dùng read_memory tới120word |
| Scenario EPC/TID | Implemented start/stream/stop/restore | Auto-restore anten chỉ1/4/8port; EPC hoặc TID-only |
| Scenario scene/phase | Implemented theo demo V6.8 | Cần firmware xác nhận |
| Real-time/trigger/heartbeat | Implemented | Config75 hiện tại; mode76 persistent; active chỉ21/76/77 |
| Read/write normal/extended | Implemented | Read1..120/write1..32word |
| Targeted EPC/password/read-back | Implemented | Target ổn định/new target; không atomic |
| Native WriteEPC04 | Implemented1..14word | Single physical tag, errata |
| Select/Lock/Kill/BlockWrite/Erase | Implemented | Phụ thuộc chip/memory/lock/power |
| CFG7/8/9/10/11/31 | Implemented | TagFocus cần tag phù hợp |
| CFG25/29 | Raw Get + validated Set6/5byte | Caller xác nhận cfg25_length=6/cfg29_length=5; không pad10byte |
| Region/profile/DRM | Implemented | Native IDs; chưa helper kHz band21/29 |
| Buffer length/count/clear/read | Implemented | Buffer16port cần xác nhận Ant width |
| GPIO/LED/buzzer | Implemented | Hai output theo phần nhất quán; module phải expose pin |
| Temperature/return loss | Implemented | Cần sensor; return-loss Ant1..4,grid100/125kHz |
| NXP protection/EAS,QT/EM4325 | Unsupported theo scope | Cần yêu cầu/chứng cứ chip riêng |
| ISO18000-6B/NATION wire emulator | Ngoài scope | Không triển khai |

Hardware_verified không tự bật từ tên model/unit test. Historical traces dùng làm nguồn vector, không đổi nhãn thành hardware test mới.
