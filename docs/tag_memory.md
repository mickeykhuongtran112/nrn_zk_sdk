# Bộ nhớ và thao tác tag
API dùng bytes và word16bit. Word address của memory không phải bit address của mask.

| Bank | ID | Ghi chú |
|---|---|---|
| Reserved | 0 | Kill password word0..1, Access word2..3; mỗi password32bit |
| EPC | 1 | CRC word0, PC word1, EPC từword2 |
| TID | 2 | Mô tả chip/serial tùy tag; thường factory locked |
| User | 3 | Có thể không tồn tại hoặc dung lượng nhỏ |

read_memory dùng02/15,1..120word; write_memory dùng03/16,1..32word. Extended có start address16bit, tự chọn khi >255. SDK kiểm tra word count, address overflow, bytes chẵn và tổng frame; không chia nhỏ write hay retry tự động.

TagTarget chọn full EPC1..15word hoặc TagMask(bank1..3, bit_address0..16383, bit_length1..255, data). Bit thấp ngoài mask phải0. Không target nghĩa unfiltered; reader/tag quyết định tag được thao tác. Dùng full TID đủ phân biệt tag khi cần định danh ổn định.

## Ghi và xác nhận

verify=True làm write -> read cùng một deadline, trả steps và confirmation. Write ACK + read đúng = read_back_verified; ACK + mismatch/error = partial. Host timeout sau TX chưa biết ghi xảy ra hay chưa = unknown; không tự retry. Cancel trong verify giữ ACK đã nhận và bước verify chưa hoàn thành ở last_result.

write_epc thực hiện đọc PC -> giữ11bit không thuộc length -> ghi PC+EPC một lần từword1 -> verify. Không đụng CRCword0. EPC mới tối đa31word theo PC và write32word. Nếu target là EPC cũ, bắt buộc verification_target mới; TID mask ổn định thường phù hợp hơn. Không khẳng định write nhiều word là atomic trên tag.

write_epc_single sử dụng04, cần đúng một physical tag trong vùng RF, hiện giới hạn1..14word vì manual mâu thuẫn. Không dùng04 tự động thay targeted write.

set_access_password ghi32bit ởReservedword2 và verify bằng password mới. set_kill_password ghiword0 và vẫn xác thực bằng Access password. Ghi password không tự Lock. Khi gọi write_memory trực tiếp chồng lên Access password, cần verification_password.

## Select / Lock / Kill / Block

select_tag mã hóa Gen2 Select bằng mask bit, select target, action, truncate và antenna mask. lock_tag có LockTarget và LockProtection, target tường minh. Permanent lock/unlock có thể không đảo được. kill_tag cần target và Kill password khác0; lệnh có tác dụng vĩnh viễn trên tag thực.

BlockWrite10 có budget riêng phụ thuộc độ dài EPC/mask; không áp giới hạn32word của03. BlockErase07 có1..120word, EPC bắt đầu từword1 trở lên. Cả hai phụ thuộc tag hỗ trợ optional command. Memory locked/overrun/power lỗi giữ nativeFC và nested tag_error.

SDK không triển khai NXP protection/QT/EM4325 chỉ từ tên chip. Các hàm thuộc tag_features báo unsupported, không nằm trong chức năng đã xác minh.
