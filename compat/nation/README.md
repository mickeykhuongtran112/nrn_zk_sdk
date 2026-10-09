# NATION reference
nrn.py là bản nguyên trạng tại commit trong [UPSTREAM.md](UPSTREAM.md); license gốc ở [LICENSE](LICENSE). Hash source/license có baseline test. Không sửa driver này trong đợt phát triển native ZK.

Driver upstream dùng blocking/threading và pyserial. Core/adapterZK không import nó. Wheel không chứa bản reference; sdist giữ reference+license phục vụ kiểm thử provenance từ clean source.

mapping_cases.json có3conversioncase kiểm chứng offline và2unverifiedcaseRF/RSSI. Adapter runtime nằm src/zk_rfid/compat/nation. [Contract](../../docs/nation_comparison.md) mô tả rõ giới hạn; comparator không thay hardware comparison.

Không commit hoặc mởCOM. Khi bảo trì upstream sau này cần regression/evidence và CHANGELOG riêng; licenseNATION không tự áp dụng mãSDKZK.
