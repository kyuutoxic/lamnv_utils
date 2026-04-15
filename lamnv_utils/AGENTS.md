# Working Rules

- Trước khi làm task, phải đọc đủ ngữ cảnh liên quan:
  - code hiện tại của phần sẽ sửa
  - tài liệu trong `docs/ai` của module liên quan
  - cấu hình, flow tích hợp, message người dùng hoặc hành vi hiện có nếu task đụng đến chúng
- Nếu `docs/ai` còn thiếu hoặc lệch so với code, phải cập nhật phần cần thiết trước hoặc trong lúc làm task, không để đến cuối mới phát hiện lệch.
- Mọi thay đổi làm thay đổi hành vi chức năng phải cập nhật tài liệu trong `docs/ai` trước khi kết thúc task.
- Nếu thay đổi thuộc một module, phải cập nhật tối thiểu:
  - `docs/ai/<module>/README.md`
  - `docs/ai/<module>/implementation/README.md`
  - tài liệu chuyên đề liên quan nếu có, ví dụ `docs/ai/<module>/telegram/README.md`
- Nếu thêm lệnh, action, settings, integration flow hoặc thay đổi format phản hồi, tài liệu phải phản ánh đúng behavior mới.
- Không kết thúc task ở trạng thái code đã đổi nhưng `docs/ai` chưa đồng bộ.
