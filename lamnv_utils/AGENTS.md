# Working Rules

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
