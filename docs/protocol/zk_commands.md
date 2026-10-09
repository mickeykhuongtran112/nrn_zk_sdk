# Danh mục command đã triển khai
Tất cả dòng dưới đây có native builder/decoder và public API hoặc lifecycle handler. Hardware chưa được xác minh trong project. [Danh mục symbol](../functions_implemented.md) có chữ ký và dòng nguồn.

| Opcode hex | Public API / nhiệm vụ |
|---|---|
| 01 | inventory_once EPC/TID/FastID; start_inventory ANSWER loop |
| 02 /15 | read_memory normal/extended |
| 03 /16 | write_memory normal/extended; targeted write_epc/password |
| 04 | write_epc_single |
| 05 /06 | kill_tag / lock_tag |
| 07 /10 | block_erase / block_write |
| 0F | inventory_single |
| 18 | inventory_to_buffer |
| 19 | inventory_once với MIX |
| 1A | inventory_matching_epc |
| 21 /4C | get_reader_info / get_serial_number |
| 22 /9E | set_region / get_region |
| 24 /25 /28 | set_address / set_inventory_time / set_baudrate |
| 2F /94 | set_power / get_power |
| 33 /40 | pulse_indicator / set_buzzer |
| 3F /66 | set_antennas / set_antenna_check; getter từ21 |
| 46 /47 | set_gpio / get_gpio |
| 50 /51 | Scenario start/stop, InventorySession quản lý |
| 6A | set_interface(usb/uart), hiệu lực sau power cycle |
| 6E | get/set_return_loss_threshold |
| 70 /71 | set/get_buffer_length: max ID16 hoặc62byte |
| 72 /73 /74 | read_buffer / clear_buffer / get_buffer_count |
| 75 /76 /77 | set_real_time_config / set_working_mode / get_working_mode |
| 78 | get/set_heartbeat_interval,30s mỗi đơn vị |
| 79 /7A | set/get_write_power |
| 7B | get/set_write_retries |
| 7F | get/set_profile, legacy hoặc extended16bit |
| 90 | get/set_drm |
| 91 /92 | measure_return_loss / get_temperature |
| 93 | stop_inventory cho pending01; không có ACK93 |
| 9A | select_tag |
| EA /EB | set/get_config, các wrapper typed bên dưới |
| EE | Notification tag/heartbeat; không phải host request |

## Extended config

| CFG decimal | Getter/setter typed | Nội dung |
|---|---|---|
| 7 | get/set_scan_parameters | interval10ms,dwell100ms,count |
| 8 | get/set_tag_focus | bool, tag-dependent |
| 9 | get/set_query_parameters | Q/session/phase; demo có scene sessions |
| 10 | get/set_tid_parameters | word address/count,0count=EPC |
| 11 | get/set_inventory_mask | mask bit, None để bỏ mask |
| 25 | get/set_config | Raw getter; setter6byte khi caller xác nhận dialect |
| 29 | get/set_config | Raw getter; setter5byte khi caller xác nhận dialect |
| 31 | get/set_custom_profiles | Ba profile IDBE16 |

Native profile catalogue gồm54record có Tari/BLF/encoding theo manual, ở src/zk_rfid/profiles.py. Danh mục không chứng minh mọi firmware hỗ trợ tất cả profile.

## Side effect và persistence

Các API có persist=False (power, antennas, region, RFprofile, CFG) mặc định volatile; encoding cờ lưu khác nhau theo command và được xử lý riêng. Không suy ra rằng các setter không có tham số persist là volatile. Đặc biệt75/76 ghi cấu hình/mode lưu;6A yêu cầu power cycle. ACK thành công chỉ xác nhận command; test power cycle còn pending.

Inventory phát RF, cập nhật/ảnh hưởng buffer và trạng thái inventoried tag. Thay maxID buffer70 làm clear. Lock/Kill/permanent protection và tag writes tác động tag theo chip. API giữ status13 partial khi áp dụng nhưng lưu thất bại, và FC+tag_error cho lỗi tag.

[Errata](errata.md) là phần của contract. Raw console không dùng để lách lifecycle stream/stop hoặc giả hỗ trợ vendor commands.
