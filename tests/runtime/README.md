# CPython / Pyodide runtime checks

Runtime SDK là một file `src/zk_rfid.py`. `run_pyodide.mjs` chỉ copy file này vào `/sdk/zk_rfid.py`; không copy cây package. `test_standalone.py` copy file sang thư mục tạm và chạy Python với `-I -S` để bỏ site-packages/PYTHONPATH, chặn import module SDK con và dependency serial khi import. Test chạy cùng golden vectors/lifecycle harness, kiểm tra type hints, pickle và lỗi thiếu pyserial khi mở transport.
Đã chạy cùng core source và bộ8golden TX vector trên CPython3.14.6/Windows và Pyodide314.0.7 (Python3.14.2, Emscripten), ngày2026-10-09.

Kết quả runtime_checks.py:2000frame RX phân mảnh từng byte; inventory; phase begin/end integer + độ/radian theo convention Ex10 V6.8; RSSI mapping người dùng raw−135 và metadata; write/read-back; cancellation sauTX;0task còn rò sauclose. Đây là tải mô phỏng hữu hạn, không phải soak testRF/browser hay đo giới hạn bộ nhớ nhiều giờ.

```powershell
python -m pytest tests/runtime -q
npm install --prefix local_data/pyodide pyodide@314.0.7
node tests/runtime/run_pyodide.mjs local_data/pyodide/node_modules/pyodide/pyodide.mjs
```

Harness Node copy source vào FS Pyodide, tạo transport async trong memory và gọi cùng Python checks. Không WebSerial, không mởCOM, không UIbridge. Core không import serial/threading/OS/subprocess; testAST phát hiện các import này ngoài transport tùy chọn. bytes conversion dùng Python bytes ở contract; bridge JS thực do ứng dụng cung cấp cần kiểm thử vòng đời proxy riêng.

Dependencies Pyodide nằm local_data bị ignore; project không phụ thuộc thư mục đó để import hoặc chạy CPython tests. Version3.11 là minimum khai báo củaSDK; CI matrix kiểm tra3.11/3.14 khi chạy.
