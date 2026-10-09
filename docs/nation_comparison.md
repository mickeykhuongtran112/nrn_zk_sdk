# Quan hệ với Nextwaves NATION
Bản upstream nguyên trạng ở compat/nation/nrn.py, commit d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b. Hash nguồn và license có regression test. Native ZK và adapter không import hoặc đóng gói nrn.py vào wheel.

Mục tiêu là mức độ tổ chức SDK: codec/transport/lifecycle/config/tag/inventory, examples, diagnostics và tests. Adapter này có contract async mới; không drop-in thay driver blocking/threading NATION.

| Contract | Trạng thái hiện tại |
|---|---|
| SDK/reader information, capability | Chuyển cấu trúc, giữ dữ liệu và evidence native |
| Power dictionary port->dBm | Read-modify-write, giữ các port không được yêu cầu đổi |
| Antenna IDs/mask, enable/disable/save | Chuyển bitmask; getter16port chưa verified |
| Inventory | Async session; callback sync/async ngoài RX; chọn một port/session |
| EPC hex / targeted EPC write | Hex lossless, readPC/write/verify; target mới sau đổi EPC |
| Memory | Dùng trực tiếp native reader API; không dựng NATION wire frame |
| Profile / band getter | Native ZK ID và Region; không khẳng định tương đương NATION |
| Profile setter | Yêu cầu RFMapping confirmed kèm evidence, do caller cung cấp |
| RF band setter | Unverified; không áp mapping đoán |
| RSSI-dBm | Approximate: chuyển tiếp mapping ZK do người dùng đặt `raw - 135`, kèm raw/source/in-range. Chưa xác minh tương đương RF với NATION |
| Phase | Native ZK có begin/end raw, độ/radian theo convention demo Ex10 V6.8; không khẳng định tương đương phase NATION. Xem [nguồn](phase_and_live_view.md) |
| Beeper | Quiet và beep-per-tag; beep-after-inventory unsupported |
| Beeper getter / native filter setting | Unsupported trong contract adapter |

CommandResult giữ native status, nested tag_error, outcome và steps. Không đổi mọi lỗi về boolean false; giữ nguồn RSSI quy đổi và không tạo PC giả. Duration callback runner dùng giây; callback failure chạy stop trong finally.

compare_results.py đọc mapping_cases.json:3 conversion case có expected độc lập (hex/power/ZK TX),2 case unverified (RF/RSSI). Comparator là công cụ offline; không chứng minh hai reader tương đương RF. R2000/E710 khác radio/firmware; Tari/BLF/encoding/session và hiệu năng cần đo với cùng điều kiện.

Không sửa nrn.py trong đợt triển khai native ZK; các thay đổi upstream sau này cần evidence, regression và CHANGELOG riêng.
