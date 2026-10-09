# Graphite Light — giao diện ZK Test Console

## Quyết định thiết kế

Áp dụng **Minimalism & Swiss Style**, biến thể **Graphite Light** cho công cụ kiểm thử RFID. Ưu tiên xám nhạt theo yêu cầu người dùng; lưới rõ ràng, chữ dễ đọc, ít bóng, không gradient/hiệu ứng trang trí. Màu ngữ nghĩa chỉ xuất hiện ở success, warning/simulator, failure/unknown.

Nguồn tham khảo: [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), commit `50d8a7de0900119855614541f15a1a616691eb33`; đã đọc [SKILL.md](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/50d8a7de0900119855614541f15a1a616691eb33/.claude/skills/ui-ux-pro-max/SKILL.md) và quick-reference.

Tra cứu thực tế:
- `"developer tool minimal gray" --design-system --variance 2 --density 7`: style phù hợp, nhưng palette dark và cấu trúc FAQ không hợp app này.
- `"operations dashboard light minimal" --design-system --variance 2 --density 8`: tiếp tục chọn Minimalism & Swiss Style, palette trắng/đen phù hợp hướng trung tính; layout marketing trả về vẫn không hợp workflow thiết bị.
- `"minimalism swiss" --domain style`: match chính xác style `minimalism-and-swiss-style`, phù hợp professional tools/dashboard.
- `"neutral gray" --domain color`: có palette documentation neutral grey, tham khảo khả năng đọc.

Không có match layout công cụ thiết bị phù hợp sau lần truy vấn lại; bố cục dưới đây là quyết định riêng của project theo workflow hiện có. Không lưu nguyên output chưa phù hợp làm design system. Palette xám, font hệ thống và phân cấp nội dung đã được điều chỉnh theo yêu cầu người dùng.

## Tokens

Các giá trị nằm ở `:root` của `static/style.css`; component dùng tên ngữ nghĩa.

| Vai trò | Giá trị |
|---|---|
| Canvas | #F4F4F3 |
| Surface | #FFFFFF |
| Surface subtle | #F8F8F7 |
| Selected surface | #EAEAE8 |
| Main text | #262626 |
| Secondary / muted text | #525252 / #656565 |
| Primary button | #373735; hover #232322; text #FFFFFF |
| Layout border / input border | #DEDEDB / #898985 |
| Success | #246445 trên #EDF5EF |
| Warning / simulator | #775414 trên #FBF5E8 |
| Failure / unknown | #9F3539 trên #FBEFEF |
| Focus | #525252, outline 2px + offset 3px |
| Card / control radius | 10px / 6px |
| Spacing scale | 4, 8, 12, 16, 20, 24, 32px |

Font giao diện: Segoe UI Variable Text / Segoe UI / system-ui; dữ liệu: Cascadia Code / Consolas / monospace. Font có sẵn phù hợp app Windows chạy offline; không tải Google Fonts hoặc thêm thư viện CSS/JS runtime. Base 16px, form 14px desktop/16px mobile, dữ liệu 12–13px; nhãn nhỏ 10–12px.

## Bố cục và tương tác

- Header nhận diện app, nguồn thiết bị/simulator; sidebar nhóm thao tác với icon SVG nét thống nhất.
- Connection → trạng thái reader/report → command và result → bảng tag → transaction log.
- Desktop rộng từ 1280px: command/result hai cột. Dưới 1280px: một cột. Dưới 768px: navigation thành lưới, form co giãn; dưới 480px: form phức tạp một cột.
- Chỉ bảng dữ liệu/log cuộn trong vùng riêng; page không tràn ngang.
- Active navigation có nền/viền/chữ đậm và `aria-current`. SVG trang trí dùng `aria-hidden`.
- Tag được chọn có nền xám/viền cạnh, ghi rõ EPC/TID ở status; hỗ trợ Enter/Space.
- Log có nút chi tiết dùng được bằng Tab/Enter. Không dựng lại bảng khi dữ liệu không đổi; giữ focus theo tag/event và giữ vị trí cuộn nếu người dùng đang xem phía trên.
- Skip link, focus ring, nhãn field, region có thể focus và live result status. Kết quả vẫn có chữ SUCCESS/FAILURE/PARTIAL/UNKNOWN; không chỉ dựa vào màu.
- Hover 180ms, không dịch chuyển kích thước. `prefers-reduced-motion: reduce` tắt transition/animation.
- 72 thao tác và Connect/Disconnect giữ nguyên contract SDK. Thay đổi nằm ở HTML/CSS/JS của test app.

## Kiểm tra ngày 2026-10-09

- 10 integration tests của demo app pass; `node --check` pass.
- Render và parse JSON thành công 72 form trên browser; không có lỗi JavaScript trong các luồng đã thử.
- Đọc FastID trên simulator, chọn TID và mở log bằng Tab/Enter hoạt động.
- Kiểm tra 375, 768, 1024, 1440px: không page overflow ngang; lưới desktop hai cột hoạt động.
- Kiểm tra tương phản từ computed styles tại màn Reader/simulator: 211 phần tử có text, không cặp nào dưới 4.5:1; minimum 4.84:1. Đây là kiểm tra trên các trạng thái đã render, không phải chứng nhận WCAG toàn ứng dụng.
- Có rule reduced-motion trong CSS; không thay tùy chọn hệ điều hành để kiểm tra.
- Không mở COM hoặc thay cấu hình module thật trong lần thay theme.

## Bổ sung live view và measurements

- Tag dùng luồng đẩy NDJSON riêng, cập nhật ô DOM bằng requestAnimationFrame; log và state tách riêng. Chọn raw integer/degrees/radians, tách phase begin/end, ghi rõ convention và RSSI raw.
- Hiển thị Active session và dropped reports. Kiểm tra trên simulator: đếm từng report150ms, Pause log không dừng đếm, reload vẫn giữ tổng (404→410), Stop báo0dropped, Clear về0 và Disconnect thành công; không có JavaScript error ở các luồng này.
- Kiểm tra lại viewport375px: page scrollWidth bằng clientWidth360px; bảng tag cuộn riêng. Desktop1440px render đủ hai cột phase. Ảnh kiểm tra: artifacts/zk-demo-live-phase.jpg.
- Xem [nguồn phase/RSSI và kiểm thử luồng trực tiếp](../../docs/phase_and_live_view.md).
