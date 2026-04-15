---
phase: requirements
title: Requirements & Problem Understanding
description: Clarify the problem space, gather requirements, and define success criteria
---

# Requirements & Problem Understanding

## Problem Statement

Module `room_rental_expense` giải quyết nhu cầu quản lý chi phí thuê phòng trọ cá nhân ngay trong Odoo 19, thay cho cách ghi chép rời rạc bằng sổ tay, chat hoặc bảng tính.

Các vấn đề chính mà module đang xử lý:

- Quản lý thông tin phòng, chủ phòng và lịch sử thuê ở nhiều nơi, thiếu một nguồn dữ liệu duy nhất.
- Ghi chỉ số điện nước hàng tháng thủ công, dễ sai khi công tơ bị thay hoặc cần chỉnh tay mức tiêu thụ.
- Tạo hóa đơn tiền phòng, điện, nước và tiện ích khác thủ công, khó theo dõi số đã trả và còn nợ.
- Theo dõi các khoản phát sinh như sửa chữa, vệ sinh, cọc và sự cố phòng không tập trung.
- Cần một kênh nhập liệu nhanh qua Telegram cho chỉ số công tơ, tra cứu danh sách và thao tác hóa đơn cơ bản.

## Goals & Objectives

### Primary goals

- Quản lý danh mục phòng trọ cùng thông tin chủ phòng và giá thuê mặc định.
- Lưu cấu hình giá điện, nước và các tiện ích theo từng phòng, có ngày hiệu lực.
- Ghi nhận chỉ số điện nước theo tháng, bao gồm trường hợp thay công tơ và nhập tay mức tiêu thụ.
- Tạo hóa đơn tự động từ chỉ số công tơ, áp giá cấu hình phù hợp theo thời điểm.
- Theo dõi trạng thái hóa đơn: `draft`, `pending`, `partially_paid`, `paid`, `overdue`, `canceled`.
- Quản lý chi phí phát sinh, tiền cọc, sự cố và lịch sử phòng.
- Hỗ trợ nhập chỉ số, xem danh sách chỉ số, tạo/xem danh sách hóa đơn và cập nhật thanh toán qua Telegram webhook.

### Secondary goals

- In hóa đơn PDF.
- Tạo nhắc việc thanh toán bằng `mail.activity` trước ngày đến hạn.
- Cung cấp màn hình báo cáo/pivot/graph cho hóa đơn và chi phí.
- Hiển thị số tiền theo định dạng VND dễ đọc trong backend.

### Non-goals

- Không tích hợp kế toán Odoo chuẩn như `account.move`.
- Không quản lý nhiều người thuê, hợp đồng thuê hoặc vòng đời tenancy chi tiết.
- Không có cổng thanh toán online hoặc đối soát ngân hàng tự động.
- Không có phân quyền chi tiết ngoài `base.group_user`.

## User Stories & Use Cases

- Là người quản lý phòng trọ cá nhân, tôi muốn lưu thông tin phòng và chủ phòng để tra cứu nhanh toàn bộ hồ sơ liên quan.
- Là người ghi chỉ số hàng tháng, tôi muốn hệ thống tự lấy chỉ số tháng trước để giảm thao tác nhập.
- Là người dùng, tôi muốn xử lý trường hợp thay công tơ điện/nước mà vẫn tính đúng mức tiêu thụ.
- Là người lập hóa đơn, tôi muốn tạo hóa đơn từ một bản ghi chỉ số công tơ để tránh nhập lặp dữ liệu.
- Là người theo dõi thanh toán, tôi muốn biết hóa đơn nào đã trả, trả một phần, quá hạn hoặc bị hủy.
- Là người dùng Telegram, tôi muốn dùng các lệnh slash như `/reading P101 350 28` để cập nhật chỉ số nhanh từ điện thoại.
- Là người dùng Telegram, tôi muốn xem danh sách hóa đơn và chỉ số gần nhất của một phòng để tra cứu nhanh mà không phải vào Odoo.
- Là người kiểm soát chi phí thuê, tôi muốn theo dõi thêm chi phí phát sinh, tiền cọc và sự cố của từng phòng.

## Success Criteria

- Mỗi phòng có thể lưu độc lập thông tin cơ bản, chủ phòng, ảnh, giá thuê và dữ liệu liên quan.
- Mỗi chỉ số công tơ có thể sinh tối đa một hóa đơn.
- Hóa đơn tự tính đúng tổng tiền từ tiền thuê, điện, nước, tiện ích khác, phí khác và giảm giá.
- Hệ thống ngăn sửa chỉ số công tơ đã gắn hóa đơn và ngăn sửa các trường lõi của hóa đơn sau khi rời trạng thái nháp.
- Telegram webhook xử lý được các lệnh hiện có:
  `/help`, `/reading`, `/inv`, `/show`, `/invoices`, `/readings`, `/paid`, `/pay`, `/unpaid`.
- Tin nhắn không bắt đầu bằng `/` không được xử lý nghiệp vụ và phải trả về thông báo hướng dẫn.
- Cron hằng ngày cập nhật hóa đơn quá hạn và tạo hoạt động nhắc thanh toán gần hạn.

## Constraints & Assumptions

### Technical constraints

- Chạy trên Odoo `19.0.1.0.0`.
- Module chỉ phụ thuộc `base`, `web`, `mail`.
- Dữ liệu được quản lý trong các model custom, không dùng module accounting chuẩn.
- Webhook Telegram dùng HTTP public route và gọi trực tiếp Telegram Bot API bằng `urllib`.

### Business constraints

- Thiết kế thiên về use case cá nhân hoặc quy mô nhỏ, không tối ưu cho vận hành nhiều tòa nhà với phân quyền phức tạp.
- Một bản ghi chỉ số công tơ được xem là đại diện cho kỳ hóa đơn của một phòng trong một ngày ghi chỉ số.

### Assumptions

- Người dùng nội bộ đều thuộc `base.group_user` và được cấp toàn quyền CRUD trên các model của module.
- Phòng được nhận diện trong Telegram qua `telegram_code`, hoặc fallback sang `room_number`/`name`.
- Giá cấu hình áp dụng theo cấu hình gần nhất có `effective_date <= reference_date`.

## Questions & Open Items

- Chưa có test tự động trong module; cần xác nhận mức độ bao phủ mong muốn.
- Cần làm rõ có cần ràng buộc duy nhất cho chỉ số theo `(room_id, reading_date)` hay chưa.
- `room.history.total_spent` hiện cộng toàn bộ hóa đơn và chi phí của phòng liên kết, không giới hạn theo `from_date/to_date`; cần xác nhận đây là chủ đích hay thiếu logic lọc kỳ.
