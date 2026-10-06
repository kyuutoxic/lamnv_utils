# Chỉ dẫn cho room_rental_expense

Áp dụng cho các file trong module này, cùng với `AGENTS.md` ở gốc workspace. Tài liệu kiến trúc và nghiệp vụ duy nhất là `../../AI_PROJECT_CONTEXT.md`; dùng bảng **Đọc theo task** để chọn phần cần đọc.

## Ranh giới và nơi đặt thay đổi

- Giữ cấu trúc addon Odoo: `models/` cho ORM/nghiệp vụ, `controllers/` cho HTTP, `views/` cho UI XML, `data/` cho defaults/sequence/cron, `security/` cho quyền, `reports/` cho QWeb, `static/src/` cho assets.
- Model custom, field, XML ID, route và method đang được caller sử dụng là interface hiện có; kiểm tra tham chiếu trước khi đổi tên hoặc di chuyển.
- File Python mới phải được import qua `__init__.py` đúng tầng. XML/data/assets mới phải được khai báo trong `__manifest__.py`, với thứ tự load phù hợp.
- Ưu tiên tên file theo model hoặc trách nhiệm rõ ràng. Không tạo file `utils.py`/`helpers.py` gom các nghiệp vụ không liên quan; không tách file chỉ theo số dòng.

## Đọc các điểm liên kết khi sửa

- Tiền/trạng thái: đọc `models/room_invoice.py` cùng caller, totals phòng, breakdown, view và report liên quan.
- Công tơ: đọc `models/meter_reading.py` cùng sync invoice và view; phân biệt onchange UI với guard ORM.
- Telegram: đọc controller, command handlers trong meter_reading và settings command payload; đối chiếu cú pháp, help và format phản hồi.
- Quyền: đọc ACL, route auth/sudo và kiểm tra sender; không xem readonly/invisible UI là ràng buộc server.
- Menu/list/assets: đọc custom XML/JS và chỉ phần OCA trực tiếp liên quan nếu cần.

## Kiểm chứng và bàn giao

- Chọn test/smoke flow theo phần 13 của context. Nếu chưa có runtime Odoo/database test, ghi rõ phạm vi kiểm tra tĩnh; không gọi đó là kiểm thử tích hợp thành công.
- Tests đặt trong `tests/`, import trong `tests/__init__.py`; kiểm tra chúng không bị `.gitignore` loại bỏ. Chạy bằng test runner Odoo với database riêng.
- Không sửa bug/giới hạn đã liệt kê trong context ngoài phạm vi task. Khi behavior thay đổi, cập nhật phần nghiệp vụ, giới hạn, bảng đọc/sửa và hướng dẫn kiểm chứng liên quan trong context chung.
