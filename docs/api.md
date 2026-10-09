# Public API

Entry point: `ZKReader(transport, address=0, capabilities=ReaderCapabilities(...), timeout=3.0)`.
[Catalogue đầy đủ](functions_implemented.md) chứa function/property, chữ ký và dòng nguồn; [JSON](api_symbols.json) dùng cho công cụ.

## Kết quả

Lệnh reader/tag trả `CommandResult[T]`:

- outcome: success/failure/partial/unknown.
- data đã decode; raw_data giữ payload gốc.
- command/status/tag_error native; FC+04 là lỗi memory locked của tag.
- confirmation: none/transmitted/acknowledged/read_back_verified.
- steps giữ kết quả từng bước; diagnostics giữ nguyên nhân.
- require_success() ném OperationError kèm result nếu không success.

Status13 là partial: cấu hình có thể đã áp dụng nhưng lưu mất nguồn thất bại. ACK không chứng minh persistence qua power cycle.

Validation/state/unsupported/unverified và deadline khi chờ khóa có thể ném exception trước TX. Timeout/disconnect sau TX trả unknown, khóa connection và không retry. CancelledError được truyền lại; xem last_result/last_inventory_outcome và state.

## Vòng đời

open/close/async context manager; constructor không I/O. Một RX consumer thuộc Dispatcher, một ordinary request, đăng ký pending trước TX. Broadcast chỉ cho một reader point-to-point, không hỗ trợ nhiều reader đồng thời trên RS485.

Deadline monotonic bao trùm chuỗi PC/read/write/verify và adapter read-modify-write. Stop93 bypass khóa request01. open() trên phiên đang chạy không reset state.

Sau timeout/cancel/EOF phải thiết lập boundary sạch. open(recover=True) là xác nhận của caller đã kết thúc operation cũ và stale bytes không thể đến, ví dụ reset module/transport. Đóng/mở COM đơn thuần không chứng minh RF dừng.

## Inventory

inventory_once/single/matching_epc trả InventoryOutcome: reports hợp lệ, status/statistics, termination_reason, complete, received_count/dropped_count. Complete nói về giao dịch, **không chứng nhận đã đọc đủ tag ngoài hiện trường**.

start_inventory(mode,config,queue_size) trả InventorySession, async iterator TagReport hoặc Heartbeat. Dùng stop trong finally hoặc async context. Outcome của stream giữ counters; consumer lưu các report đã nhận. Queue đầy báo QueueOverflow và dropped_count.

- Answer loop: config mỗi round;01 dừng bằng93. Mix19 không có interrupt theo manual, phải chờ round kết thúc.
- Scenario: snapshot/set volatile/read-back CFG9/10/11, tạm chọn anten,50/EE/51; khôi phục sau stop ACK. EPC hoặc TID-only theo CFG10; không tự bật FastID/Mix.
- Real-time: dùng config75 hiện tại; đọc77 xác định EPC/TID,76=1/2 để chạy,76=0 để dừng. Mode persistent. Q/phase/anten của Answer config không tự biến thành config75; gọi set_real_time_config trước.

Device timeout/buffer-full, byte loss hoặc thiếu memory trong Mix là partial. Host timeout giữ tags hợp lệ. Report sau stop ACK làm state unknown để không lẫn với phiên mới.

## Memory/tag

read_memory(bank,word_address,word_count,target,access_password):1..120word.
write_memory(bank,word_address,data,...):1..32word, bytes chẵn. Extended15/16 tự chọn khi start address>255 hoặc explicit extended_format. Không chia write/retry tự động.

TagTarget(epc=bytes) dùng full EPC1..15word. TagTarget(mask=TagMask(bank,bit_address,bit_length,bytes)) dùng bank1..3,address0..16383,length1..255; padding thấp bằng0. None nghĩa unfiltered, không bảo đảm một tag.

verify=True yêu cầu target còn hợp lệ. Nếu ghi thay EPC/PC/vùng mask, phải cung cấp verification_target; nên dùng TID ổn định. Ghi trực tiếp Access password phải có verification_password. Helper set_access_password tự dùng password mới cho read-back.

write_epc đọc PC, giữ11bit không phải length, ghép PC+EPC vào một targeted write từ word1 rồi verify. Không ghi CRC word0. write_epc_single là opcode04, cần đúng một physical tag; chỉ1..14word do errata.

lock_tag dùng LockTarget/LockProtection; kill_tag cần target và password khác0. BlockWrite tính frame budget251byte riêng; BlockErase1..120word, EPC WordPtr>=1. Chip tag có thể không hỗ trợ optional command. Ghi password khác lock.

## Đơn vị, persistence

Power0..30dBm nguyên; get_power tuple theo thứ tự port. set_power mặc định tạm thời. Write power bit7 là enable, không phải persistence.

Region là native band/min/max channel. Helper trả kHz cho bảng liên tục; band21/29 chưa quy đổi vì công thức mơ hồ. Profile mặc định extended uint16; legacy phải chọn explicit, không fallback âm thầm sau Set.

Scan time100ms; indicator50ms; heartbeat30s; Real-time pause trong10/20/30/50/100ms, filter seconds. Baud ACK dùng baud cũ rồi transport đổi baud; interface hiệu lực sau power cycle.

RSSI giữ unsigned raw; `rssi_dbm = rssi_raw - 135` theo hai mốc người dùng đặt60→−75,110→−25. Helper `rssi_to_dbm(raw)` không clamp; report có `rssi_source` và `rssi_in_calibration_range` để phân biệt ngoại suy ngoài60..110. Chưa phải hiệu chuẩn RF tuyệt đối. Phase có `phase_raw`, hai integer BE16 `phase_begin_raw`/`phase_end_raw`, và các field `phase_begin_degrees`, `phase_end_degrees`, `phase_begin_radians`, `phase_end_radians`. Quy ước Ex10 V6.8: `(raw * 0.087) % 180` độ; không phải hiệu chuẩn phase tuyệt đối. Hai helper public `phase_to_degrees(raw, wrap=True)` và `phase_to_radians(raw, wrap=True)` hỗ trợ bỏ folding khi `wrap=False`. Field cũ số ít `phase_radians` giữ None. FrequencyBE24kHz khi có. Thiếu field dùng None. Timestamp host monotonic không phải RF timestamp. Xem [nguồn, đơn vị và live view](phase_and_live_view.md).

## Ví dụ ghi User

```python
from zk_rfid import MemoryBank, TagMask, TagTarget
# Thay bằng TID đủ phân biệt tag thử nghiệm có User bank.
tid = bytes.fromhex("E28000000000000000000001")
target = TagTarget(mask=TagMask(MemoryBank.TID, 0, len(tid)*8, tid))
result = await reader.write_memory(
    MemoryBank.USER, 0, bytes.fromhex("00011234"), target=target, verify=True
)
result.require_success()
print(result.confirmation, result.steps)
```

## Structured trace và GUI

```python
from zk_rfid import ZKReader

# Observer đồng bộ phải trả về nhanh; đưa event vào queue nếu cần I/O.
reader = ZKReader(transport, on_event=events.append)
```

`TraceEvent` có sequence, timestamp monotonic, kind, exchange_id, command/address/status, raw bytes và detail. Các event gồm request, tx, rx, frame, response_complete, result, state, connected/disconnected, timeout/fault/cancelled/parser_loss. RX chunk có thể chứa nhiều frame nên không gán một exchange_id giả. Result của lệnh thường giữ ID giao dịch; multi-step operation phải xem cả steps trong CommandResult và các exchange liên quan.

`logging.getLogger("zk_rfid.trace").setLevel(logging.DEBUG)` bật trace qua logging khi ứng dụng đã cấu hình handler. SDK không tự cài handler. Observer exception được đếm trong `reader.dispatcher.trace.observer_errors`; observer không được block RX hoặc gọi lại reader đồng bộ. Trace không thay thế outcome/confirmation từ API.

[GUI trong tests/demo_app](../tests/demo_app/README.md) dùng observer này, file writer riêng, bảng tag và export CSV/JSONL. [Bảng đối chiếu NATION/C#](demo_and_parity.md) phân biệt chức năng đã có với vendor extensions còn thiếu.
