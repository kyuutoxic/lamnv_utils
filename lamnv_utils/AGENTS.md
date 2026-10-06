# Working Rules

## Điểm vào và thứ tự đọc

- Workspace này chứa addon Odoo trong `project/` và dependency OCA trong `addons_oca/`.
- Bắt đầu bằng phần **Đọc theo task** và phần 1 của `AI_PROJECT_CONTEXT.md`, sau đó đọc các phần được chỉ dẫn cho task hiện tại.
- Khi làm trong `project/room_rental_expense/`, đọc thêm `project/room_rental_expense/AGENTS.md` để áp dụng quy tắc riêng của module.
- `AGENTS.md` chỉ chứa chỉ dẫn làm việc; kiến trúc, nghiệp vụ, cấu hình và giới hạn được mô tả trong `AI_PROJECT_CONTEXT.md`. Không chép lại cùng một mô tả ở nhiều file.

## Ngữ cảnh và tài liệu

- Trước khi làm task, phải đọc đủ ngữ cảnh liên quan:
  - code hiện tại của phần sẽ sửa
  - các phần liên quan trong `AI_PROJECT_CONTEXT.md`
  - cấu hình, flow tích hợp, message người dùng hoặc hành vi hiện có nếu task đụng đến chúng
- `AI_PROJECT_CONTEXT.md` là tài liệu tổng hợp duy nhất của project; không tạo lại cây tài liệu theo từng phase/module.
- Nếu context còn thiếu hoặc lệch so với code, phải cập nhật phần cần thiết trước hoặc trong lúc làm task, không để đến cuối mới phát hiện lệch.
- Mọi thay đổi làm thay đổi hành vi chức năng phải cập nhật các phần liên quan trong `AI_PROJECT_CONTEXT.md` trước khi kết thúc task.
- Nếu thêm lệnh, action, settings, integration flow hoặc thay đổi format phản hồi, tài liệu phải phản ánh đúng behavior mới.
- Phân biệt hành vi đã triển khai, đề xuất và kết quả đã kiểm chứng; không ghi test đã pass nếu chưa chạy.
- Không đưa mật khẩu, bot token hoặc secret thật vào tài liệu.
- Không kết thúc task ở trạng thái code đã đổi nhưng context chưa đồng bộ.

## Quy trình mỗi task

1. Xác định module, hành vi cần sửa và phạm vi người dùng đã yêu cầu; kiểm tra Git status để nhận diện thay đổi đang có.
2. Đọc context theo bảng điều hướng, source trực tiếp và các caller/dependency liên quan. Task đụng đến tiền, trạng thái, liên kết hoặc quyền phải đọc phần quy tắc và giới hạn tương ứng.
3. Chỉ sửa trong phạm vi task; giữ nguyên thay đổi đang có của người dùng. Không sửa dependency OCA chỉ vì nằm cùng workspace.
4. Chạy kiểm chứng phù hợp với thay đổi. Thay tài liệu thì kiểm tra đường dẫn/tham chiếu; thay nghiệp vụ thì kiểm chứng flow và ràng buộc liên quan. Không dùng database hoặc bot thật để thử khi chưa có yêu cầu phù hợp.
5. Đồng bộ context và báo cáo ngắn gọn thay đổi, kết quả thực sự đã kiểm tra, phần chưa kiểm chứng.

## Khi thiếu hoặc mâu thuẫn ngữ cảnh

- Yêu cầu mới nhất của người dùng quyết định phạm vi và behavior mong muốn; code hiện tại quyết định behavior đang triển khai. Context là bản mô tả cần đối chiếu, không phải bằng chứng runtime.
- Nếu phát hiện context lệch code, đọc caller/config liên quan rồi sửa phần lệch; không tự đổi behavior chỉ để khớp tài liệu.
- Khi tiếp tục sau gián đoạn, đọc lại Git status/diff, phần context của task và các file đang sửa; không dựa vào việc AI nhớ toàn bộ cuộc trò chuyện.
- Nếu thêm module, thêm một `AGENTS.md` ngắn trong module để ghi chỉ dẫn riêng và bổ sung module vào context chung. Không tạo cây README theo phase hoặc bản sao context.
