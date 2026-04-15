---
title: Telegram Integration Guide
description: Concise setup and usage guide for Telegram in room_rental_expense
---

# Telegram Integration Guide

## Mục đích

Telegram trong `room_rental_expense` dùng để:

- ghi chỉ số điện nước
- tạo hóa đơn từ chỉ số đã ghi
- xem hóa đơn
- xem danh sách hóa đơn
- xem danh sách chỉ số
- cập nhật thanh toán

Quy ước:

- tất cả lệnh phải bắt đầu bằng `/`
- nếu tin nhắn không bắt đầu bằng `/`, bot chỉ trả về thông báo hướng dẫn

Code liên quan:

- `project/room_rental_expense/controllers/telegram_webhook.py`
- `project/room_rental_expense/models/meter_reading.py`

## 3 parameter cần điền

Vào `Settings -> Technical -> Parameters -> System Parameters`:

```text
room_rental_expense.telegram_bot_token =
room_rental_expense.telegram_webhook_secret =
room_rental_expense.telegram_allowed_chat_ids =
```

- `telegram_bot_token`: token từ `@BotFather`
- `telegram_webhook_secret`: secret dùng khi set webhook
- `telegram_allowed_chat_ids`: danh sách `chat.id`, ngăn cách bằng dấu phẩy

Template rỗng:

- [system-parameters-template.md](./system-parameters-template.md)

Trong `Settings`, module đã có nút `Đăng ký lệnh Telegram` để tự gọi Telegram `setMyCommands`.

## Tạo bot và lấy token

1. Mở `@BotFather`
2. Gửi `/newbot`
3. Nhập tên bot
4. Nhập username kết thúc bằng `bot`
5. BotFather trả token dạng:

```text
123456789:AAExampleTokenHere
```

6. Điền token vào:

```text
room_rental_expense.telegram_bot_token
```

## Lấy `telegram_allowed_chat_ids`

Phải lấy bằng `chat.id`, không phải username.

Luồng đúng:

1. Nếu bot đang có webhook, gọi:

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
```

2. Mở chat với bot, bấm `Start` hoặc gửi:

```text
/start
```

3. Gọi:

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

4. Tìm trong JSON:

```json
{
  "result": [
    {
      "message": {
        "chat": {
          "id": 123456789
        }
      }
    }
  ]
}
```

5. Điền vào:

```text
room_rental_expense.telegram_allowed_chat_ids = 123456789
```

Lưu ý:

- chat cá nhân: số dương, ví dụ `123456789`
- group/supergroup: số âm, ví dụ `-1009876543210`
- khi webhook đang bật thì `getUpdates` không dùng được

## Chuẩn bị dữ liệu phòng

Nên luôn khai báo `telegram_code` duy nhất cho từng phòng.

Ví dụ:

```text
name = Phòng 101
room_number = 101
telegram_code = P101
default_rent = 3500000
```

Bot tìm phòng theo thứ tự:

1. `telegram_code`
2. `room_number`
3. `name`

## Webhook

Route của module:

```text
/room_rental_expense/telegram/webhook
```

Ví dụ webhook production:

```text
https://odoo.example.com/room_rental_expense/telegram/webhook
```

Lưu ý:

- route chỉ nhận `POST`
- phải là URL HTTPS public
- mở URL này trên browser không phải cách test đúng

## Chạy local

Telegram không gọi được `localhost`, nên local phải dùng tunnel HTTPS.

Ví dụ:

- Odoo local: `http://127.0.0.1:8069`
- tunnel: `https://abc123.ngrok-free.app`

Webhook URL:

```text
https://abc123.ngrok-free.app/room_rental_expense/telegram/webhook
```

Ví dụ với `ngrok`:

```bash
ngrok http 8069
```

## Chạy server

Ví dụ:

```text
https://odoo.example.com/room_rental_expense/telegram/webhook
```

## Set webhook

Ví dụ:

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://odoo.example.com/room_rental_expense/telegram/webhook&secret_token=<YOUR_SECRET>
```

Kiểm tra:

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Sau khi điền `telegram_bot_token`, bạn có thể vào `Settings` và bấm `Đăng ký lệnh Telegram` để Telegram gợi ý các lệnh khi người dùng gõ `/`.

## Đăng ký command suggestions

Sau khi điền `telegram_bot_token`, vào `Settings` và bấm:

```text
Đăng ký lệnh Telegram
```

Telegram sẽ gợi ý các lệnh:

```text
/help
/reading
/inv
/show
/invoices
/readings
/paid
/pay
/unpaid
```

Kết quả tốt:

- `ok = true`
- `result.url` đúng URL webhook
- không có `last_error_message`

Lỗi thường gặp trong `getWebhookInfo`:

- `403 Forbidden`: secret sai
- timeout / connection error: domain không public, tunnel tắt, proxy sai
- SSL error: HTTPS/certificate lỗi

## Flow local ngắn nhất

1. Tạo bot, lấy token
2. Điền:

```text
room_rental_expense.telegram_bot_token = 123456789:AAExampleTokenHere
room_rental_expense.telegram_webhook_secret = room-rental-local-secret
room_rental_expense.telegram_allowed_chat_ids =
```

3. Chạy Odoo local
4. Chạy:

```bash
ngrok http 8069
```

5. Lấy `chat.id` bằng `deleteWebhook` -> `/start` -> `getUpdates`
6. Điền `telegram_allowed_chat_ids`
7. Gọi `setWebhook`
8. Test:

```text
/help
/reading P101 350 28
/inv P101 2026-04-15
```

Nếu tunnel đổi URL, phải `setWebhook` lại.

## Lệnh hỗ trợ

```text
/help
/reading P101 350 28
/reading P101 350 28 2026-04-15
/reading room:P101 elec:350 water:28
/reading room:P101 elec:350 water:28 date:2026-04-15
/inv P101 2026-04-15
/show INV-2026-0001
/invoices P101
/readings P101
/paid INV-2026-0001
/pay INV-2026-0001 1000000
/unpaid INV-2026-0001
```

Ý nghĩa nhanh:

- `/show INV-2026-0001`: xem chi tiết một hóa đơn, gồm cả phần `Chi tiết` để gửi cho chủ nhà
- `/invoices P101`: xem tối đa 10 hóa đơn gần nhất của phòng
- `/readings P101`: xem tối đa 10 chỉ số gần nhất của phòng

## Hành vi quan trọng

- bot tự lấy chỉ số tháng trước để tính usage
- nếu số hiện tại nhỏ hơn tháng trước, bot sẽ báo lỗi
- Telegram flow không hỗ trợ case thay công tơ
- reading đã gắn hóa đơn thì không cập nhật qua Telegram được
- mỗi reading chỉ gắn tối đa một hóa đơn
- `/show` có thêm khối `Chi tiết` lấy từ `manual_breakdown`

## Lỗi thường gặp

- `invalid_secret`: secret trong webhook không khớp parameter
- không phản hồi: chưa set webhook, URL không public, tunnel tắt, token sai
- không tìm thấy phòng: chưa có `telegram_code` hoặc mã gửi lên không khớp
- chỉ số nhỏ hơn tháng trước: nhập sai hoặc là case thay công tơ
- reading đã gắn hóa đơn: không cập nhật lại qua Telegram được

## Checklist

- [ ] tạo bot bằng `@BotFather`
- [ ] điền `telegram_bot_token`
- [ ] lấy `chat.id` bằng `getUpdates`
- [ ] điền `telegram_allowed_chat_ids`
- [ ] điền `telegram_webhook_secret`
- [ ] tạo `telegram_code` cho phòng
- [ ] set webhook
- [ ] bấm `Đăng ký lệnh Telegram`
- [ ] test `/help`
- [ ] test ghi chỉ số
- [ ] test `INV`

## Tham chiếu

- [Module Overview](../README.md)
- [Implementation](../implementation/README.md)
- https://core.telegram.org/bots/api
