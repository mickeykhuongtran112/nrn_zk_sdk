# Kế hoạch phát triển ZK RFID SDK và đối chiếu NATION

- Cập nhật: 2026-10-09.
- Workspace: `zk-rfid-sdk`; distribution: `zk-rfid-sdk`; module một file: `zk_rfid`.
- Vai trò: firmware engineer tự phát triển driver protocol Python, debug trước khi bàn giao.
- Trạng thái đợt này: native SDK 0.2.0.dev1 (một file nguồn) đã triển khai và kiểm thử phần mềm CPython/Pyodide; hardware/power-cycle/RF benchmark và license phát hành chưa hoàn tất.
- Bản đầu đã commit/push theo yêu cầu chủ dự án. Đợt gộp một file là bản 0.2.0.dev1; không đổi tên workspace hoặc di chuyển dữ liệu riêng.

## 1. Mục tiêu và ranh giới

Xây SDK native ZK-7180M/ZK-7182M ở cùng cấp độ host protocol với Nextwaves nrn.py: tự tạo byte command, nhận/giải mã response/report/error và cung cấp API có kiểu dữ liệu, đơn vị, trạng thái rõ ràng. ZK là SDK chính, hoạt động độc lập với NATION.

Chỉ hỗ trợ RAIN UHF Gen2/ISO18000-6C và các chức năng reader liên quan. Bỏ ISO18000-6B và các chuẩn ngoài phạm vi. Tính năng riêng của chip tag chỉ triển khai khi có nhu cầu và bằng chứng; tên E710 không chứng minh firmware có mọi chức năng Gen2v2/Ex10.

Core Python async hướng tới CPython và Pyodide. Transport được inject; pyserial là dependency tùy chọn của CPython. Phạm vi ban đầu loại GUI/web. Theo yêu cầu bổ sung ngày 2026-10-09, thêm HTML test console trong tests/demo_app, loopback HTTP/serial do CPython quản lý; core async không phụ thuộc web; SerialTransport tùy chọn dùng asyncio.to_thread cho pyserial. Không triển khai extension, dịch vụ mạng dùng chung hoặc COM ảo.

NATION có hai vai trò riêng:
- `compat/nation/`: driver nguyên trạng, provenance/license và ca đối chiếu ngoài package.
- `NationAdapter` trong `src/zk_rfid.py`: adapter API runtime trên ZK, chỉ hỗ trợ contract/mapping đã chốt.

Không triển khai bộ giả lập NATION wire protocol. Adapter không import nrn.py hoặc phụ thuộc parser/transport NATION. SDK ZK được nghiệm thu độc lập với mapping NATION.

“Đầy đủ” nghĩa là có danh mục chức năng và trạng thái rõ theo model/firmware, không suy đoán hoặc giả kết quả cho chức năng chưa xác minh.

## 2. Kết quả triển khai phần mềm
- Native codec/parser/dispatcher/reader/inventory/tag/RF/config/transport đã thay scaffold.
- Examples và console/capture/replay/comparator thực thi được; import/--help không mở COM.
- Public API có type hints/docstrings, native errors, partial/unknown và evidence.
- Unit/integration/compat/runtime đã chạy. Pyodide dùng cùng source,8golden vectors và2000fragmented RXframes, không rò task trong harness.
- Danh mục thực tế tự sinh: [functions_implemented.md](docs/functions_implemented.md), [api_symbols.json](docs/api_symbols.json).
- [Validation](docs/validation.md) lưu môi trường/kết quả; [supported matrix](docs/supported_devices.md) phân biệt implemented và unverified.
- nrn.py/reference LICENSE giữ nguyên. LICENSE mã ZK chưa chọn; chưa phát hành package lên PyPI.
- Đợt GUI có 72 thao tác trong menu + Connect/Disconnect, structured TX/RX trace, CSV/JSONL và simulator. Xem [GUI](tests/demo_app/README.md), [đối chiếu NATION/C#](docs/demo_and_parity.md).
- Người dùng báo 3 hardware tests PASS; agent đã kiểm tra một phiên Scenario/phase trên COM13/115200/1-port ở bản trước, xem docs/hardware_live_view_check.md. Đợt gộp file chỉ kiểm thử phần mềm, không gửi lệnh phần cứng. Dữ liệu riêng bị ignore và loại khỏi package.

## 3. Tree project và trách nhiệm

Theo yêu cầu tích hợp/review, từ 0.2.0.dev1 toàn bộ implementation nằm trong `src/zk_rfid.py`; không duy trì các module nguồn con hoặc bản generated song song. Import trực tiếp `from zk_rfid import ...`; tests/demo/examples dùng đúng file này.

README trong các thư mục fixture/runtime giữ thư mục trong Git và mô tả dữ liệu cần có. local_data được ignore nên chỉ tồn tại cục bộ.

```text
zk-rfid-sdk/  # Native SDK implementation
├── README.md                                         # Giới thiệu, cài đặt và trạng thái kiểm chứng
├── pyproject.toml                                    # Cấu hình package Python, dependency tùy chọn và công cụ
├── LICENSE                                           # Trạng thái giấy phép của mã project; chưa chọn license phát hành
├── CHANGELOG.md                                      # Lịch sử thay đổi SDK và cấu trúc project
├── .gitignore                                        # Bỏ qua dữ liệu riêng, môi trường Python, cache và build
├── plan_agent.md                                     # Kế hoạch triển khai và tiêu chí nghiệm thu
├── src/
│   └── zk_rfid.py                                   # Toàn bộ SDK: API, types/errors, protocol, command,
│                                                    # transport, dispatcher, inventory và NationAdapter
├── compat/                                           # Tài liệu và mã tham chiếu ngoài package phát hành
│   └── nation/                                       # Baseline NATION để đối chiếu và sửa lỗi riêng
│       ├── README.md                                 # Cách quản lý và dùng bản tham chiếu
│       ├── UPSTREAM.md                               # Commit, nguồn và hash của bản nrn.py gốc
│       ├── LICENSE                                   # License MIT nguyên trạng của SDK NATION upstream
│       ├── CHANGELOG.md                              # Lịch sử thay đổi riêng của bản NATION
│       ├── nrn.py                                    # Driver NATION nguyên trạng tại commit đã chốt
│       └── mapping_cases.json                        # Manifest các ca mapping; hiện chưa có ca xác minh
├── examples/                                         # Ví dụ API dự kiến; scaffold chưa mở cổng hoặc thao tác thiết bị
│   ├── reader_info.py                                # Đọc thông tin reader
│   ├── get_set_power.py                              # Get/set công suất và kiểm tra kết quả
│   ├── inventory_answer.py                           # Inventory từng lượt command-response
│   ├── inventory_scenario.py                         # Fast inventory EPC hoặc TID theo CFG
│   ├── inventory_fastid.py                           # EPC + TID bằng FastID trên tag hỗ trợ
│   ├── inventory_mix.py                              # EPC kèm đọc vùng nhớ được cấu hình
│   ├── read_memory.py                                # Đọc Reserved/EPC/TID/User theo word
│   ├── write_user_memory.py                          # Ghi User và read-back
│   ├── write_epc.py                                  # Ghi EPC, chọn tag và xác minh
│   └── nation_adapter.py                             # Sử dụng contract NATION qua adapter ZK
├── tools/                                            # Công cụ debug và đối chiếu cho firmware engineer
│   ├── serial_console.py                             # Gửi/giải mã lệnh trong phiên debug
│   ├── capture_serial.py                             # Capture TX/RX, timestamp và metadata phiên
│   ├── replay_capture.py                             # Replay frame/chunk và trạng thái
│   └── compare_results.py                            # Kiểm chứng mapping offline; không phải wrapper runtime
├── tests/                                            # Unit/integration/runtime và hardware opt-in
│   ├── demo_app/                                     # HTML local, catalogue, controller, trace/log và simulator
│   ├── unit/                                         # Kiểm thử logic thuần không cần thiết bị
│   │   ├── test_crc.py                               # Vectors CRC độc lập và frame sai
│   │   ├── test_frame_parser.py                      # Chunk, length, CRC, nhiễu và recovery
│   │   ├── test_status.py                            # Success/error/continuation/partial/timeout theo command
│   │   ├── test_inventory.py                         # Request và report EPC/TID/FastID/Mix
│   │   ├── test_tag_access.py                        # Bank, word/bit, password, độ dài và PC
│   │   └── test_reader_config.py                     # Cấu hình reader, RF, power và anten
│   ├── integration/                                  # Transport giả và replay nhiều thành phần
│   │   ├── test_dispatcher.py                        # Routing, response muộn, notification và disconnect
│   │   ├── test_inventory_session.py                 # Start/stop, completion và chuyển luồng đọc
│   │   └── test_memory_operations.py                 # Select/read/write/read-back và kết quả chưa xác định
│   ├── hardware/                                     # Chỉ chạy có chủ đích trên reader/tag mẫu
│   │   ├── test_reader_config.py                     # Get/set và persistence theo model/firmware
│   │   ├── test_inventory_modes.py                   # Khả năng Answer/Scenario và loại dữ liệu
│   │   └── test_tag_memory.py                        # Bank, dung lượng chip, bảo vệ và ghi thực
│   ├── runtime/                                      # CPython/Pyodide: import, async, bytes và tài nguyên
│   │   └── README.md                                 # Yêu cầu runtime harness; chưa có test Pyodide thực thi
│   └── compat/                                       # Kiểm thử riêng cho tham chiếu và adapter
│       └── nation/                                   # Regression NATION và mapping
│           ├── test_nrn.py                           # Regression cho lỗi NATION được sửa có bằng chứng
│           ├── test_mapping.py                       # Quy tắc quy đổi, unsupported và unverified
│           └── test_adapter.py                       # Contract input/output/event của adapter
├── fixtures/                                         # Dữ liệu kiểm thử chọn lọc được quản lý bằng Git
│   ├── zk/                                           # Vectors ZK có provenance
│   │   ├── captured/                                 # Trace thật; không gán nhãn captured cho dữ liệu giả
│   │   │   └── README.md                             # Metadata cần có cho capture ZK
│   │   ├── documented/                               # Vectors trích tài liệu, chưa thay thế kiểm chứng phần cứng
│   │   │   └── README.md                             # Nguồn/trang/errata cho vector tài liệu
│   │   └── synthetic/                                # Vectors tạo có chủ đích để kiểm tra biên/lỗi
│   │       └── README.md                             # Mô tả cách tạo và kỳ vọng của vector giả lập
│   └── nation/                                       # Vectors NATION riêng biệt với ZK
│       ├── captured/                                 # Trace thật N701/N704
│       │   └── README.md                             # Metadata capture NATION
│       ├── documented/                               # Vectors tài liệu/upstream có nguồn
│       │   └── README.md                             # Quy tắc provenance cho vectors NATION
│       └── synthetic/                                # Vectors giả lập NATION
│           └── README.md                             # Điều kiện và kỳ vọng của dữ liệu tự tạo
├── docs/                                             # Tài liệu kỹ thuật SDK
│   ├── scope.md                                      # Phạm vi Gen2/6C và phần loại trừ
│   ├── api.md                                        # Contract public dự kiến, đơn vị, async và kết quả
│   ├── supported_devices.md                          # Ma trận chức năng; chưa công bố hardware verified
│   ├── inventory_modes.md                            # Answer/Scenario/Real-time và ma trận dữ liệu
│   ├── tag_memory.md                                 # Bank, word/bit, PC/password/lock/read-back
│   ├── validation.md                                 # Phân cấp chứng cứ và quy trình kiểm thử
│   ├── inventory_benchmark.md                        # Recall, stray tags, latency và độ lặp lại
│   ├── nation_comparison.md                          # Phạm vi tương thích và các quyết định mapping
│   └── protocol/                                     # Đặc tả protocol làm căn cứ triển khai
│       ├── zk_frame.md                               # Frame/length/endian/CRC theo manual
│       ├── zk_commands.md                            # Danh mục command Gen2 và reader được ưu tiên
│       ├── zk_tag_report.md                          # EPC/TID/FastID/Mix, measurement và completion
│       └── errata.md                                 # Mâu thuẫn manual, bằng chứng và trạng thái xác minh
└── local_data/                                       # Ignore toàn bộ; không phải dependency của SDK/test
    ├── zk/                                           # Tài liệu và dữ liệu ZK làm việc riêng
    └── nation/                                       # Tài liệu và dữ liệu NATION làm việc riêng
```

Các thư mục legacy riêng hiện giữ nguyên bên cạnh tree: `Protocol_ZK/`, `Protocol_NATION/`, `Mode_research/`. Khi chủ dự án tổ chức lại dữ liệu có thể đưa chúng vào local_data; không cần di chuyển để core hoạt động.

### 3.1. Luồng xử lý

```text
Public API / inventory session
  -> validation + capability + state
  -> command builder -> frame -> injected transport TX
  -> transport RX (một consumer)
  -> incremental parser -> dispatcher -> command/report decoder
  -> CommandResult / TagReport / InventoryOutcome
```

- reader.py quản lý API và orchestration; inventory_session.py quản lý vòng đời inventory.
- dispatcher.py sở hữu một luồng RX và pending requests; inventory session không đọc cạnh tranh transport.
- protocol/commands/mapping không I/O; không tự mở COM từ import/constructor.
- Core không import serial/threading/multiprocessing hoặc API hệ điều hành; không sleep chặn/asyncio.run.
- Chưa tạo framework plugin, code generator hoặc bộ abstraction vượt nhu cầu.
- profiles.py chứa RF profile native/tham số vật lý; mapping RF giữa hãng nằm tại adapter.
- caps reader tách khỏi khả năng chip tag, dung lượng bank và trạng thái khóa.

### 3.2. Dữ liệu và Git

Ignore toàn bộ local_data cùng ba thư mục dữ liệu riêng hiện hữu; không ignore mọi .txt/.json/.hex/.bin/.log vì fixtures cần được track.

Fixtures phải phân biệt captured/documented/synthetic và lưu nguồn, TX/RX, expected result, model/firmware/chip tag, baud/RF/anten, thời gian, chunk/timing khi liên quan. Không gọi dữ liệu ví dụ là capture thực.

Không copy toàn bộ manual, Word hoặc log private vào package. .gitignore không xóa dữ liệu đã tracked hoặc lịch sử. Không git add/commit trong đợt scaffold; các commit baseline/fix về sau chỉ làm khi được yêu cầu.

## 4. Contract SDK

### 4.1. Public API dự kiến

Chi tiết tại docs/api.md; tên/chữ ký còn cần chốt P0:
- get_reader_info(), get_capabilities().
- Get/set power, RF config, anten và reader I/O theo danh mục.
- inventory_once(), start_inventory(), stop_inventory().
- read_memory(), write_memory(), write_epc().
- Select/lock/kill/block operations theo capability.

Read/write dùng bank, word_address, word_count/data, access_password và target độc lập. Mask dùng bit_address/bit_length. Data là bytes, không mất zero đầu hoặc tự ép encoding ứng dụng.

Thao tác chờ thiết bị là async. Core không nhận trách nhiệm nghiệp vụ kiểm kho/POS/chấm công/phân kiện; examples chỉ minh họa thao tác SDK.

### 4.2. Result, errors và measurements

CommandResult giữ outcome success/failure/partial/unknown, native status, nested tag error, data và mức xác nhận. InventoryOutcome giữ termination_reason/completeness và dữ liệu hợp lệ đã nhận.

Phân biệt đã TX, ACK tiếp nhận/thành công theo semantics và read-back verified. Host timeout sau set/write có thể là unknown. Reader timeout của inventory có thể có kết quả partial, không bỏ tags.

Không tự retry thao tác có thể đã ghi. Với chuỗi lệnh/chia nhỏ dữ liệu phải báo bước/phần đã xác nhận và phần chưa rõ. Cancel host không mặc nhiên hủy reader operation.

TagReport giữ EPC/TID/memory data theo đúng loại report, bank/address nếu có, anten, RSSI/phase/frequency và nguồn timestamp. Chỉ đổi sang đơn vị vật lý khi scale đã xác minh; thiếu field dùng None. Giữ raw phase/begin/end nếu còn mơ hồ. Không dùng scale phase NATION áp cho ZK.

### 4.3. Inventory: mode, dữ liệu và RF là ba trục độc lập

| Cơ chế | Lệnh/đặc điểm | Completion |
|---|---|---|
| Answer | 0x01 inventory; 0x19 Mix; host điều khiển từng lượt | Có thể nhiều frame; cần status kết thúc |
| Scenario / Ex10 fast | 0x50 start, report 0xEE, 0x51 stop | Start ACK không phải end; xác minh stop ACK/late reports |
| Real-time | 0x75 config, 0x76 mode 1/2, 0x77 get | Luồng auto/trigger riêng, command được phép bị giới hạn |

- Scenario đọc EPC khi CFG10 LenTID=0, hoặc TID theo AdrTID và LenTID=1..15 được manual/demo mô tả.
- FastID EPC+TID được mô tả ở bit5 QValue của 0x01; cần chip tag tương thích.
- Mix 0x19 lấy EPC kèm dữ liệu bộ nhớ. FastID/Mix trên Scenario chưa có contract xác minh, không tự bật.
- EPC/TID trong fast report không mặc nhiên là hai dữ liệu ghép chung; mask User không đồng nghĩa báo cáo User.
- 0x93 chỉ ngắt 0x01 và không có response riêng. Theo dõi response của lệnh đang chạy; không chờ ACK 0x93.
- State cần idle/starting/inventorying/stopping/disconnected/unknown; không kết luận dừng từ sleep hoặc im lặng.
- Đối chiếu số reads, unique IDs, read completeness và stray tags; không dùng reads/s để chứng nhận đọc đủ.
- Quy tắc RF/session/target ứng dụng được đánh giá bằng benchmark, không hard-code dựa tên Scenario/Answer.

### 4.4. Bộ nhớ tag

| Bank | ID | Phạm vi |
|---|---|---|
| Reserved | 0 | Kill/Access password, mỗi password 32 bit nếu chip triển khai |
| EPC | 1 | CRC word0, PC word1, EPC từ word2 |
| TID | 2 | Nhận dạng chip/serial tùy tag; thường factory locked |
| User | 3 | Dữ liệu ứng dụng, có thể không tồn tại |

- 0x02/0x15 read tối đa 120 word; Num=0 không hợp lệ theo API ZK này.
- 0x03/0x16 write tối đa 32 word; WordPtr thường 1 byte, extended 2 byte.
- Có opcode cho một bank không chứng minh chip cho ghi bank đó.
- Write EPC 0x04 có ràng buộc một tag trong vùng đọc; không tự thay cho targeted write.
- Ghi password khác lock; khóa ghi không tự tạo read protection.
- Write cần read-back có target còn hợp lệ sau thay đổi EPC/password. Giữ partial/unknown, không giả atomic.
- Giới hạn BlockWrite/Erase và tính năng chip riêng phải xác minh; không suy ra từ giới hạn generic write.

## 5. Nền protocol và điều phối

Baseline theo manual: TX Len/Adr/Cmd/Data/CRC; RX thêm Status; Len không tính chính nó; không có header NATION 0x5A. CRC init 0xFFFF, reflected poly 0x8408, low byte trước theo code tài liệu. Cần vectors độc lập trước implementation acceptance.

- Parser xử lý chunk tùy ý, nhiều frame, thiếu/hỏng length/CRC, nhiễu, giới hạn buffer và recovery.
- Đăng ký pending trước TX; một command thường tại một thời điểm khi không có transaction ID.
- Xử lý ngoại lệ stop đúng mode; không để stop bị xếp sau stream không kết thúc.
- Match bằng context hợp lệ; xử lý response muộn trước tái sử dụng matcher.
- Phân biệt status thường 0x00 với inventory 0x01/02/03/04/26, report 0xEE và tag error nested 0xFC.
- Device partial result khác host deadline; deadline dùng monotonic và bao trùm chuỗi nhiều bước.
- Không suy ra khoảng cách byte trên dây từ timestamp chunk OS/browser.
- CFG/profile ID có thể 16 bit; không hard-code 8 bit hoặc số anten dựa tên chip.
- Luôn kiểm tra docs/protocol/errata.md trước chốt layout.

## 6. NATION reference và runtime adapter

Baseline nguyên trạng có hash và license trong compat/nation. Chưa sửa nrn.py hoặc tạo commit; khi bắt đầu bảo trì cần baseline và regression trước sửa, giữ nguồn và CHANGELOG riêng.

Adapter API chạy trên SDK ZK, không chứa bản sao codec ZK. Contract function/result/callback/async phải chốt; không tuyên bố drop-in với nrn.py blocking/threading chỉ vì tên giống.

### 6.1. Mapping

Đối chiếu get/set (đơn vị/range/anten/persistence), inventory/control flow, EPC/TID/memory, errors, timeout, disconnect/cancel và side effects.

Mức tương đương: verified-equivalent / converted / multi-step / approximate-with-conditions / unsupported / unverified. Không tự dùng mapping gần đúng khi chưa được chủ dự án xác minh.

Chủ dự án phụ trách RF R2000/E710: Tari, BLF, modulation/encoding, profile, power/frequency, session/Q/target và measurement. Cùng số ID hoặc đơn vị không chứng minh tương đương.

### 6.2. Phân công file

- mapping.py: quy tắc runtime được kiểm chứng.
- adapter.py: áp dụng contract NATION bằng API ZK và quy tắc mapping.
- mapping_cases.json: input/expected/model/firmware/fixture/tolerance/evidence.
- compare_results.py: decode/replay riêng từng protocol rồi so kết quả; không tự tạo mapping và không phải wrapper.

Compare TX với expected TX của chính protocol. Không so CRC/frame hai hãng như nhau. Output pass/fail/unverified phải giữ khác biệt và nguồn; replay pass không thay chứng cứ RF/hardware.

## 7. Lộ trình

### S0 — Scaffold review (lịch sử)

- [x] Dựng tree, docstrings trách nhiệm và metadata package.
- [x] Thêm docs draft, examples/tools báo chưa triển khai, test placeholders.
- [x] Lưu NATION nguyên trạng với nguồn/license/hash.
- [x] Bổ sung ignore và local_data, giữ nguyên dữ liệu hiện hữu.
- [x] Không add/commit, không mở COM hoặc chạy bài ghi tag.

Đầu ra S0 là scaffold. Các giai đoạn dưới đây ghi trạng thái triển khai hiện tại.

### P0 — Chốt specification và API

- [ ] Kiểm kê model/firmware, chip tag, manual revision và nguồn capture.
- [x] Chốt ma trận command/mode/data/capability trong phạm vi Gen2/6C.
- [ ] Giải quyết errata cần thiết bằng trace; giữ unresolved khi chưa có bằng chứng.
- [x] Chốt API/models, word/bit/byte, error/result/completion và persistence.
- [x] Chốt transport contract và runtime test harness.
- [ ] Chọn license của mã project trước khi phát hành.

### P1 — Codec, parser và runtime nền

- [x] Frame/CRC/endian/length và incremental parser có buffer limits.
- [x] Vectors độc lập, fake transport và replay harness.
- [x] Builder/decoder reader info, power và inventory tối thiểu.
- [x] Kiểm tra cùng vectors trên CPython/Pyodide; async bytes/result/resource lifecycle.
- [x] Không mở rộng toàn bộ command trước khi nền tảng được kiểm chứng.

### P2 — Reader, dispatcher và inventory session

- [x] Pending matcher/deadline, one RX loop, notification routing và reconnect/cancel semantics.
- [x] Answer single round/loop, Scenario start/report/stop và Real-time riêng theo capability.
- [x] Multi-frame/partial/statistics/heartbeat/late response và stop 0x93/0x51 đúng semantics.
- [x] Serial CPython và console/capture/replay; không I/O chặn trong core.
- [x] Type hints/docstring và diagnostics đi cùng từng API.

### P3 — Memory, RF và nhóm chức năng còn lại

- [x] Read/write thường/mở rộng, target selection, EPC/password/lock/kill/block.
- [x] Read-back, partial write và unknown result khi timeout/disconnect.
- [x] RF config/profile, power/anten, buffer, I/O và diagnostics.
- [ ] Tag vendor features chỉ sau khi có nhu cầu/capability xác minh; hiện ngoài scope, báo UnsupportedFeature.
- [x] Native errors, tag payload/measurements/raw và unsupported/unverified nhất quán.

### P4 — Validation, benchmark và bàn giao native ZK

- [x] Unit/integration tests có vector độc lập và đường lỗi meaningful.
- [ ] Hardware tests trên từng model/firmware/chip tag, có TX/RX và điều kiện thử.
- [ ] Persistence power cycle, write đúng target/data và giới hạn capability.
- [ ] Benchmark completeness/stray/latency/repeatability/UART/buffer theo ca thực tế.
- [x] Pyodide replay hữu hạn2000frame, cancellation, conversion và tài nguyên; soak test nhiều giờ vẫn chưa chạy.
- [x] Examples thực thi được, API docs và supported matrix có trạng thái chính xác.
- [x] Wheel/clean checkout không phụ thuộc local_data/nrn/pyserial bắt buộc.

### C1 — Bảo trì NATION độc lập

- [x] Bản nguồn/license/provenance nguyên trạng trong scaffold.
- [x] Baseline tests; chỉ commit khi được chủ dự án yêu cầu.
- [ ] Sửa lỗi nrn có bằng chứng, regression và CHANGELOG riêng.
- [x] Không chặn bàn giao native ZK vì lỗi/mapping NATION.

### C2 — Mapping và API adapter

- [x] Chốt tập contract NATION cần giữ và semantics async/callback/result.
- [ ] Lập cases; chủ dự án xác minh mapping RF và sai khác.
- [x] Implement mapping.py, adapter.py và comparator theo contract.
- [x] Test converted/multi-step/unsupported/unverified/partial/unknown; verified-equivalent RF chưa có evidence.
- [ ] Hardware comparison khi cần; bàn giao phạm vi tương thích cụ thể.

## 8. Tiêu chí hoàn thành thực sự

Các tiêu chí phần mềm đã kiểm chứng được đánh dấu; phần hardware/trace thực và license chưa đạt nghiệm thu phát hành:
- [ ] Mỗi chức năng trong scope có implementation/evidence/model/firmware rõ.
- [ ] Byte TX/RX, response/error/report/completion đúng bằng vectors và trace phù hợp.
- [ ] Không false success, measurement giả, unsupported bị che hoặc mất report âm thầm.
- [ ] Bộ nhớ tag, inventory state/stop và timeout sau write được kiểm thử đầy đủ.
- [x] Core cùng source chạy qua runtime tests CPython/Pyodide.
- [x] Package/examples/docs có thể sử dụng từ clean checkout; dữ liệu riêng không bị đóng gói.
- [x] Mapping không suy đoán RF; contract NATION và native error được bảo toàn.
- [ ] License/version/known limitations sẵn sàng trước phát hành.

## 9. Nguồn và điểm chưa xác minh

- Manual do chủ dự án cung cấp: UHF RFID Reader Series User Manual V2.25, 106 trang; được dùng làm nguồn documented, chưa copy vào repo.
- Demo Ex10 Module SDK V6.8: đã review Answer/Scenario, CFG10 và fast reports; không đưa DLL/demo hãng vào core.
- NATION baseline: https://github.com/Nextwaves-Industries/nextwaves-sdk/tree/d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b/sdk/nation/python
- Scaffold từng tham chiếu Protocol_ZK/EPC_Phase_HOST_SEND.txt, EPC_Phase_READER_RESPONSE.txt và Mode_research/Profile.png. Chưa tìm thấy tại các đường dẫn workspace hiện tại; không dùng các file này làm bằng chứng trong đợt triển khai.
- Chứng cứ phần cứng hiện có giới hạn ở các ca ghi nhận trong docs/hardware_live_view_check.md và 3 tests do người dùng báo; chưa nghiệm thu toàn bộ model/firmware/chip tag.

## 10. Hạng mục còn lại trước nghiệm thu thiết bị/phát hành
1. Chọn module/firmware/antenna ports và chip tag thực, capture TX/RX có provenance; không lấy tên chip làm capability.
2. Xác minh errataCFG25/29,16port và các format đang bị gate; thêm regression từ capture thực.
3. Test round-trip memory, persistence qua mất nguồn, stop/late report với thời gian thực.
4. Benchmark completeness/stray/latency/repeatability theo docs/inventory_benchmark.md; chưa có số liệu RF.
5. Chọn license mã ZK trước publish. Adapter RF mapping chỉ thêm sau đo và xác nhận của chủ dự án.

Những mục này không được tự đánh dấu hoàn tất từ unit test. C1 sửa nrn chưa thực hiện vì không có defect/evidence trong phạm vi native ZK.
