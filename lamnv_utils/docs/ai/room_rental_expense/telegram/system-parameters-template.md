---
title: System Parameters Template
description: Blank master data template for room_rental_expense system parameters
---

# System Parameters Template

Điền các giá trị bên phải dấu `=` rồi nhập vào Odoo tại:

`Settings -> Technical -> Parameters -> System Parameters`

## Telegram Parameters

```text
room_rental_expense.telegram_bot_token =
room_rental_expense.telegram_webhook_secret =
room_rental_expense.telegram_allowed_chat_ids =
```

## Default Billing Parameters

```text
room_rental_expense.default_electric_price =
room_rental_expense.default_water_price =
room_rental_expense.default_wifi_price =
room_rental_expense.default_trash_fee =
room_rental_expense.default_parking_fee =
room_rental_expense.default_other_utilities_price =
room_rental_expense.reminder_days =
```

## Suggested Room Master Data Template

```text
name =
room_number =
telegram_code =
default_rent =
landlord_name =
landlord_phone =
```

## Suggested room.config Template

```text
room_id =
effective_date =
electric_price =
water_price =
wifi_price =
trash_fee =
parking_fee =
other_utilities_price =
notes =
```
