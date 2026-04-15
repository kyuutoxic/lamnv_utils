---
title: room_rental_expense AI Docs
description: Module entrypoint for room_rental_expense
---

# room_rental_expense

## Summary

Module Odoo `room_rental_expense` dùng để quản lý phòng trọ cá nhân, chỉ số điện nước, hóa đơn, chi phí phát sinh, tiền cọc, sự cố và nhắc thanh toán.

## Quick Facts

- Odoo version: `19.0`
- Module path: `project/room_rental_expense`
- Dependencies: `base`, `web`, `mail`
- Main integration: Telegram webhook

## Core Models

- `rental.room`
- `meter.reading`
- `room.invoice`
- `room.config`
- `room.expense`
- `room.deposit`
- `room.issue`
- `room.history`

## Main Flows

- quản lý thông tin phòng và chủ phòng
- cấu hình giá điện, nước và tiện ích theo ngày hiệu lực
- ghi chỉ số công tơ theo tháng
- tạo hóa đơn từ chỉ số công tơ
- theo dõi thanh toán, quá hạn và reminder activity
- nhập chỉ số và thao tác hóa đơn nhanh qua Telegram bằng lệnh slash
- xem danh sách hóa đơn và danh sách chỉ số qua Telegram
- đăng ký command suggestions Telegram ngay trong Settings

## Documentation Map

- [Requirements](./requirements/README.md)
- [Design](./design/README.md)
- [Implementation](./implementation/README.md)
- [Testing](./testing/README.md)
- [Planning](./planning/README.md)
- [Deployment](./deployment/README.md)
- [Monitoring](./monitoring/README.md)
- [Telegram Guide](./telegram/README.md)
