# lamnv_utils — ngữ cảnh project dành cho AI

> Đối chiếu source ngày **2026-10-07**. Đọc phần 1 trước để nắm nhanh; các phần sau giải thích chi tiết và chỉ đến nơi cần sửa. File này có thể đưa riêng cho AI, không cần đính kèm các README khác để hiểu kiến trúc và nghiệp vụ chính.
>
> Đây là mô tả code đang có, không phải cam kết mọi flow đã chạy thành công. Đã chạy tests Odoo 19 trên database riêng ngày 2026-10-06; phạm vi/kết quả ở phần 13. Khi sửa code, kiểm tra lại file nguồn vì tài liệu là snapshot. Không chứa mật khẩu, bot token hay webhook secret thật.

## Đọc theo task

Đọc `AGENTS.md` ở gốc và phần 1 trước. Khi sửa addon, đọc thêm `project/room_rental_expense/AGENTS.md`. Sau đó dùng bảng này để đọc có chọn lọc; không cần nạp toàn bộ source OCA cho mỗi task.

| Task | Phần context cần đọc | Source cần mở trước |
| --- | --- | --- |
| Onboarding / hỏi tổng quan | 1–4, 12 | Manifest, models/__init__.py; mở model cụ thể khi cần xác minh |
| Phòng, chủ phòng, tổng tài chính, lịch sử | 4, 6, 12 | models/rental_room.py, models/room_history.py, views/rental_room_views.xml |
| Chỉ số điện/nước, thay công tơ, khóa reading | 5, phần liên kết ở 6, 12, 13 | models/meter_reading.py, models/room_invoice.py, views/meter_reading_views.xml |
| Giá, thành phần tiền, hóa đơn | 4, 6, 8, 10, 12, 13 | models/room_config.py, models/room_invoice.py, models/rental_room.py, invoice view/report |
| Thanh toán, state, reminder | Bảng trạng thái ở 6, 7 nếu có Telegram, 9–10, 12–13 | room_invoice actions/_auto_update_status/cron, meter_reading payment handlers, cron_data.xml |
| Telegram, lệnh, response, settings | 5–7, 10, 12–13 | controllers/telegram_webhook.py, models/meter_reading.py, models/telegram_update.py, models/res_config_settings.py |
| Giao diện, menu, format số, PDF | 8, 11 nếu liên quan OCA, 13 | views/XML hoặc reports/XML hoặc static/src/js/currency_widget.js và model cung cấp dữ liệu |
| Chi phí, cọc, sự cố | 4, 8, 12–13 | model và view tương ứng; rental_room totals nếu liên quan chi phí |
| Deploy, cấu hình, bảo mật | 3, 7, 9–10, 12–13 | Manifest, ACL, controller, config đã che secrets, defaults/cron |
| Thêm feature / review / refactor | 2–4, phần nghiệp vụ tương ứng, 12–14 | File trực tiếp, caller và dependency liên quan; không chỉ đọc diff |

Đường dẫn source trong bảng tương đối với `project/room_rental_expense/`. Số phần khớp mục lục bên dưới. Bảng này chỉ là điểm bắt đầu; nếu source gọi sang phần khác thì đọc thêm phần đó trước khi sửa.

### Vai trò của từng file hướng dẫn

```text
AGENTS.md                              quy tắc chung + quy trình lấy ngữ cảnh
AI_PROJECT_CONTEXT.md                  kiến trúc/nghiệp vụ/flow + bảng điều hướng
project/room_rental_expense/AGENTS.md    quy tắc riêng của addon Odoo
source + tests                         behavior thực tế + bằng chứng kiểm chứng
```

Chỉ dẫn riêng của module không lặp lại mô tả nghiệp vụ. Không có cấu trúc file nào bảo đảm AI luôn hiểu đúng: mỗi task vẫn phải đọc source liên quan, đối chiếu context và kiểm chứng. Quy trình này giảm việc bỏ sót ngữ cảnh và giảm tài liệu trùng lặp.

Quy ước thư mục và đặt tên source của addon dựa trên [Odoo 19 coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html). Cách tổ chức ba file hướng dẫn ở đây là lựa chọn cho workspace này, không phải yêu cầu bắt buộc của Odoo.

## Mục lục

1. [Nắm project trong 2 phút](#1-nắm-project-trong-2-phút)
2. [Cấu trúc và ranh giới repository](#2-cấu-trúc-và-ranh-giới-repository)
3. [Kiến trúc và dependency](#3-kiến-trúc-và-dependency)
4. [Mô hình dữ liệu](#4-mô-hình-dữ-liệu)
5. [Chỉ số công tơ và mức tiêu thụ](#5-chỉ-số-công-tơ-và-mức-tiêu-thụ)
6. [Hóa đơn, áp giá và thanh toán](#6-hóa-đơn-áp-giá-và-thanh-toán)
7. [Telegram: giao thức và flow](#7-telegram-giao-thức-và-flow)
8. [Giao diện, widget và PDF](#8-giao-diện-widget-và-pdf)
9. [Cron và reminder](#9-cron-và-reminder)
10. [Cấu hình, chạy và upgrade](#10-cấu-hình-chạy-và-upgrade)
11. [Các addon OCA có trong source](#11-các-addon-oca-có-trong-source)
12. [Điểm cần biết và giới hạn hiện tại](#12-điểm-cần-biết-và-giới-hạn-hiện-tại)
13. [Bản đồ sửa code và kiểm chứng](#13-bản-đồ-sửa-code-và-kiểm-chứng)
14. [Quy tắc làm việc và prompt dùng lại](#14-quy-tắc-làm-việc-và-prompt-dùng-lại)

## 1. Nắm project trong 2 phút

`lamnv_utils` là workspace custom addon cho **Odoo 19**, hiện có một addon nghiệp vụ tự viết: **`project/room_rental_expense`**, version manifest `19.0.1.3.1`, author `lamnv`, license `LGPL-3`, application bật, auto-install tắt.

Mục đích là **theo dõi chi phí thuê phòng trọ cá nhân**: phòng và chủ phòng, điện nước, tiền thuê, hóa đơn, thanh toán, chi phí phát sinh, tiền cọc, sự cố, lịch sử ở. Telegram giúp nhập nhanh chỉ số và thao tác hóa đơn từ điện thoại. Tên “invoice” ở đây là hóa đơn custom của ứng dụng; không có tích hợp `account.move`, sổ kế toán hoặc cổng thanh toán.

Luồng trung tâm:

```text
rental.room (phòng, chủ phòng, default_rent)
    + room.config (giá tiện ích theo effective_date)
    + meter.reading (số cũ/mới -> usage)
          -> room.invoice (áp giá -> tính tiền -> xác nhận -> thanh toán)
                -> PDF QWeb
                -> mail.activity nhắc thanh toán qua cron

Telegram POST -> controller -> meter.reading.process_telegram_message()
              -> command handler -> các model Odoo -> sendMessage
```

Những điểm AI cần giữ đúng:

- Logic tiền và trạng thái hóa đơn nằm ở `models/room_invoice.py`; command Telegram cũng gọi ORM, không có database riêng.
- `models/meter_reading.py` giữ công tơ và parser/dispatcher slash commands; telegram_session.py điều khiển menu nhập theo bước, telegram_update.py giữ pairing/receipt, telegram_reminder.py gửi nhắc hạn, meter_reading_anomaly.py tính cảnh báo, monthly_summary.py tổng kết tháng.
- Mức tiêu thụ thường = số hiện tại − số cũ. Thay công tơ và nhập tay được hỗ trợ trong Odoo backend.
- Chỉ số trước là **bản ghi gần nhất có ngày nhỏ hơn ngày đang xét**, không bắt buộc tháng liền trước.
- Tạo hóa đơn từ UI chỉ số để lại nháp; `/inv` tạo mới sẽ tự xác nhận nếu tổng tiền > 0.
- Đã có hóa đơn thì khóa các trường lõi của reading và chặn xóa reading. Hóa đơn rời `draft` thì khóa các trường lõi; tiền đã trả và ghi chú vẫn sửa được.
- Chỉ một hóa đơn được liên kết với một reading qua constraint khai báo `unique(meter_reading_id)`. Chưa có unique phòng/ngày hoặc phòng/tháng cho reading/hóa đơn.
- Telegram hỗ trợ slash command và reply keyboard/menu có phiên nhập. Slash room lookup dùng OR telegram_code/room_number/name; menu có thể chọn phòng bằng ID. Receipt vẫn chống xử lý trùng update_id.
- Secret bắt buộc; allowlist bắt buộc cho lệnh nghiệp vụ/menu. Pairing chỉ ngoại lệ allowlist khi có mã hợp lệ. Webhook sử dụng sudo.
- Local config đặt port `1369`, database `room_rental_dev`, `workers=0`, **`max_cron_threads=0`**. Có cron trong addon không đồng nghĩa cron chạy trên local này.
- Tests riêng trong `project/room_rental_expense/tests/` dùng TransactionCase cho ORM/nghiệp vụ và HttpCase cho webhook. Test trong OCA không thay thế tests phòng trọ.

## 2. Cấu trúc và ranh giới repository

```text
lamnv_utils/
├── AGENTS.md                         quy tắc chung và thứ tự đọc theo task
├── AI_PROJECT_CONTEXT.md             file onboarding độc lập này
├── config/local.conf                cấu hình instance local; có dữ liệu bí mật
├── project/room_rental_expense/
│   ├── AGENTS.md                     chỉ dẫn riêng của addon Odoo
│   ├── __manifest__.py, __init__.py
│   ├── models/                       nghiệp vụ + receipt/session/reminder Telegram + summary/anomaly + settings
│   ├── controllers/telegram_webhook.py
│   ├── security/ir.model.access.csv
│   ├── data/                         sequence, mặc định, cron
│   ├── views/                        10 XML view/menu/settings
│   ├── reports/invoice_template.xml
│   ├── tests/                        TransactionCase và HttpCase
│   ├── migrations/19.0.1.1.0/        tính lại status/tổng khi upgrade
│   └── static/
│       ├── src/js/currency_widget.js
│       └── description/              icon.png, room_icon.png, index.html
└── addons_oca/addons_oca/web/          bộ OCA web 19.0, có source/test/docs riêng
```

Odoo core nằm **ngoài workspace này** theo `addons_path` (`../odoo/odoo/addons`, `../odoo/addons`); còn có addon path ngoài repo `~/code/learn_odoo`. Không suy luận module ở đó tồn tại hoặc đã cài chỉ từ config.

Phạm vi tổng hợp: source nghiệp vụ Python/XML/JS/ACL/data/report, tài liệu module, local config đã che secrets, manifest và các thành phần OCA. Thư viện đóng gói Bokeh/Fuse, ảnh, bản dịch `.po/.pot` là dependency/assets; không diễn giải từng dòng mã minified hoặc từng chuỗi dịch trong tài liệu này. Tình trạng module đã cài, database và deployment thật không xác minh được từ source.

## 3. Kiến trúc và dependency

Manifest khai báo đầy đủ:

| Dependency | Vai trò |
| --- | --- |
| `base` | ORM, user, settings, sequence, cron |
| `web` | backend client, views, registry, report layout |
| `mail` | chatter, tracking, activity |
| `web_responsive` | launcher/menu và trải nghiệm backend responsive |
| `web_tree_many2one_clickable` | nút mở record Many2one từ list |
| `web_group_expand` | mở/đóng nhóm trong grouped list |

`web_responsive` còn phụ thuộc `web_tour`, `mail`, `web`, và khai báo loại trừ `web_enterprise`. Các addon OCA khác nằm trong source không tự động trở thành dependency của phòng trọ.

Addon root import models/controllers; models/__init__.py import nghiệp vụ, settings, telegram_update, monthly_summary, telegram_reminder, meter_reading_anomaly và telegram_session. Controller import qua controllers/__init__.py.

Thứ tự load dữ liệu: ACL → sequence → system parameters → cron → report → các views → menu. Asset custom duy nhất được manifest đưa vào `web.assets_backend` là `currency_widget.js`. Không có frontend SPA/build npm riêng cho nghiệp vụ.

Odoo ORM quản lý PostgreSQL; binary ảnh có `attachment=True` dùng cơ chế attachment/filestore Odoo. Telegram outbound dùng `urllib` tiêu chuẩn; cron dùng `dateutil.relativedelta`.

## 4. Mô hình dữ liệu

Tất cả đường dẫn model trong bảng thuộc `project/room_rental_expense/models/`.

| Model / file | Dữ liệu và trách nhiệm |
| --- | --- |
| `rental.room` / `rental_room.py` | Phòng, địa chỉ, tòa nhà, diện tích, loại phòng, thời gian thuê, ảnh, chủ phòng, ngân hàng, `telegram_code`, `default_rent`, tổng tài chính |
| `room.config` / `room_config.py` | Giá điện, nước, wifi, rác, xe, tiện ích khác theo phòng và ngày hiệu lực |
| `room.telegram.update` / `telegram_update.py` | Receipt nội bộ chống xử lý trùng update theo SHA-256 token bot và update_id; không lưu token/message thật, không cấp ACL cho người dùng thường |
| `meter.reading` / `meter_reading.py` | Ngày/tháng ghi, số điện/nước cũ/mới, thay công tơ, usage/manual override, ảnh, liên kết hóa đơn; Telegram |
| `room.invoice` / `room_invoice.py` | Kỳ/ngày/số hóa đơn, hạn trả, thành phần tiền, chiết khấu, đã trả/còn lại, trạng thái, breakdown, giá áp dụng, reading |
| `room.expense` / `room_expense.py` | Chi phí riêng theo ngày, category, description, amount, ảnh biên lai |
| `room.deposit` / `room_deposit.py` | Số/ngày cọc, dự kiến hoàn, số/ngày hoàn, status, ảnh biên lai |
| `room.issue` / `room_issue.py` | Sự cố, category, severity, status, ngày phát hiện/báo/khắc phục, ảnh |
| `room.history` / `room_history.py` | Lịch sử ở, phòng liên quan optional, ngày từ/đến, chủ phòng, thuê trung bình, total_spent |
| extension `res.config.settings` / `res_config_settings.py` | TransientModel, ba field cấu hình Telegram và action đăng ký command suggestions |

### Quan hệ và tổng hợp

`rental.room` có One2many: `invoice_ids`, `meter_reading_ids`, `expense_ids`, `config_ids`, `deposit_ids`, `issue_ids`. Các child model này có `room_id` required và `ondelete='cascade'`. `room.history.room_id` optional, không có One2many history khai báo trên phòng.

Phòng và hóa đơn kế thừa `mail.thread`, `mail.activity.mixin`. Các model bổ trợ không có mixin này.

Tổng trên phòng là stored compute:

```text
total_invoiced  = sum(invoice_ids.total_amount)
total_paid      = sum(invoice_ids.paid_amount)
total_remaining = sum(invoice_ids.remaining_amount)
total_expenses  = sum(expense_ids.amount)
```

Ba tổng hóa đơn/đã trả/còn lại loại canceled, vẫn cộng draft; dependency gồm invoice status. Migration `migrations/19.0.1.1.0/post-migrate.py` cập nhật lại status hóa đơn và stored totals phòng khi nâng từ version cũ. `room.history.total_spent` vẫn là non-stored compute: tổng toàn bộ hóa đơn + chi phí của phòng liên kết, không giới hạn thời gian/trạng thái, không cộng cọc. `avg_rent` nhập tay, không tự tính.

### Selection và validation

- Loại phòng: `single`, `double`, `studio`, `shared` (default `single`). Phòng chỉ kiểm tra bắt đầu không sau kết thúc; bằng nhau được chấp nhận. Unique `telegram_code` dùng `models.Constraint` của Odoo 19.
- Giá: khai báo unique `(room_id,effective_date)`, các giá không âm. Tên compute từ tên phòng và ngày hiệu lực.
- Chi phí: `repair`, `cleaning`, `supplies`, `maintenance`, `damage_fee`, `other`. Không tự cộng khoản này vào `room.invoice.other_charges`.
- Cọc: `pending`, `confirmed`, `partial_return`, `fully_returned`, `disputed`; default `pending`. Không có action tự quyết định status theo số hoàn.
- Sự cố: category `water_leak`, `electric_problem`, `broken_furniture`, `pest`, `noise`, `temperature`, `other`; severity `low/medium/high/critical`, default `medium`; status `reported/acknowledged/in_progress/resolved`, default `reported`.
- Chi phí/cọc/sự cố là CRUD đơn giản, không có validation bổ sung về số âm, trình tự ngày hay state machine trong Python.

## 5. Chỉ số công tơ và mức tiêu thụ

Reading `_order='reading_date desc, id desc'`. `name` stored compute từ phòng và tháng; `reading_month` từ `reading_date.strftime('%m/%Y')`. Ngày, phòng, số hiện tại điện/nước required. Không có default ngày khai báo ở field.

### Tìm chỉ số trước

`_get_previous_reading(room, reading_date, exclude_id)` lấy `room.meter_reading_ids`, loại record đang sửa, lọc ngày **nhỏ hơn** ngày xét, sort theo ngày/id giảm dần. Nếu không truyền ngày, chọn record gần nhất trong tập còn lại.

- `default_get()` và onchange phòng/ngày dùng để gợi ý số cũ trong UI.
- Telegram gọi `_prepare_previous_counter_vals()` trước khi create/write.
- Không override `meter.reading.create()` để tự điền số cũ cho mọi ORM caller. Script import cần chuẩn bị dữ liệu đúng.
- Thay đổi reading cũ không có logic tự cập nhật số cũ của các reading ngày sau.

### Công thức điện/nước

Hai loại công tơ áp cùng logic:

```text
nếu manual_override: usage = manual_value
nếu không thay:       usage = current - previous
nếu thay:
  old_delta = max(replacement_last - previous, 0) nếu replacement_last khác 0
  old_delta = 0 nếu replacement_last không có hoặc bằng 0
  usage = old_delta + current
```

Giả định phần công tơ mới tính từ 0; không có field số đầu công tơ mới. Inverse khi sửa usage sẽ bật manual override và ghi manual value. Onchange tắt override reset manual value về 0 rồi tính lại tự động.

Ví dụ: previous 300, current 350 → 50 kWh. Thay công tơ, previous 300, old last 320, new current 15 → 35 kWh. Manual value 42 → 42 kWh.

Nếu current < previous và không bật cờ thay thì constraint báo lỗi, kể cả bật manual override. Khi thay và old last khác 0 mà nhỏ hơn previous cũng báo lỗi. Onchange có warning để người dùng thấy sớm; warning không thay thế validation ORM.

### Khóa reading và tạo hóa đơn

`write()` chặn thay đổi phòng/ngày/số cũ/mới/usage/cờ thay/số cuối/manual fields khi record đã có `invoice_id`. Notes, ảnh, ghi chú thay công tơ và `invoice_id` không thuộc set khóa. `unlink()` chặn xóa mọi reading đã gắn hóa đơn. Constraint trên reading kiểm tra invoice thuộc cùng phòng.

`action_create_invoice()`:

1. Đã có invoice thì mở invoice đó.
2. Chưa có: create invoice với phòng, tháng reading, ngày reading, `meter_reading_id`.
3. Gắn invoice và trả action mở form. Không tự gọi `action_confirm()` trong flow UI.

Không coi `invoice_id` trên reading là nguồn duy nhất bảo đảm đồng bộ: phần sync chính nằm trong invoice; đổi trực tiếp chiều reading có thể không cập nhật chiều invoice.

## 6. Hóa đơn, áp giá và thanh toán

### Create và mặc định

`create()` gọi `_inject_default_values()` cho dict hoặc từng dict trong list, rồi `super().create()` → `_apply_config_prices(force=True)` → `_sync_meter_readings()` → `_auto_update_status()`.

Mặc định:

- Phòng từ vals hoặc context `default_room_id`.
- Rent từ phòng nếu vals không có rent hoặc rent bằng 0 và phòng có default rent.
- Ngày lập = `fields.Date.context_today(self)` nếu không truyền.
- Tháng = tháng của ngày lập nếu không truyền; format dự kiến `MM/YYYY`.
- Hạn trả = ngày lập + 7 ngày nếu có phòng và chưa truyền hạn.
- Số = sequence `room.invoice`; XML prefix `INV-%(year)s-`, padding 4, dùng chung company. Nếu sequence không trả số, fallback literal `INV-2024-001`.
- `invoice_period_date` stored compute ngày đầu tháng từ invoice_month; sort theo kỳ, ngày lập, id giảm dần.

### Áp giá

Ngày tham chiếu = invoice_date → ngày đầu invoice_month → hôm nay. Khi invoice có ngày lập, tháng hóa đơn không quyết định ngày chọn giá.

`room._get_active_config(reference_date)` search phòng với `effective_date <= reference_date`, lấy mới nhất. Nếu không truyền reference date, method không lọc ngày hiệu lực và có thể trả cấu hình tương lai.

Có config thì lấy giá điện/nước và cộng wifi + rác + xe + tiện ích khác thành `utilities_amount`; lưu `applied_config_id`. Không có thì đọc các system parameters mặc định. `_origin` được dùng cho phòng ở onchange để xử lý NewId.

`force=True` khi create, khi write đổi phòng/tháng/ngày, và onchange tương ứng; **có thể ghi đè giá/utilities caller đã truyền**. Sau tạo có thể sửa giá trong draft. Thay đổi `room.config` không có logic tự repricing tất cả hóa đơn cũ.

### Công thức

```text
electric_amount  = electric_usage * electric_price_per_unit
water_amount     = water_usage * water_price_per_unit
subtotal         = rent_amount + electric_amount + water_amount
                 + utilities_amount + other_charges
total_amount     = subtotal - discount_amount
remaining_amount = total_amount - paid_amount
```

Tiền lưu bằng Float; format VND làm tròn để hiển thị, không phải quy tắc làm tròn số lưu. Không clamp tổng/còn lại về 0.

`manual_breakdown` compute text: nước → điện → tiện ích → phí khác → giảm giá → tiền phòng → tổng, bỏ dòng có giá trị 0. Nếu có reading, hiển thị current − previous = usage; khi thay công tơ/override, chuỗi trừ này có thể không diễn tả đúng công thức actual usage. Telegram `/show` và PDF dùng field này.

### Liên kết công tơ

`meter_reading_id` optional, `ondelete='set null'`; `meter.reading.invoice_id` cũng set null khi xóa invoice. Invoice khai báo unique meter_reading_id và constraint cùng phòng, reading không được thuộc invoice khác.

`_sync_meter_readings()` tìm reading đang trỏ invoice, tháo liên kết cũ, gắn reading được chọn, chép electric/water usage. Chỉ gọi khi create hoặc write có `meter_reading_id`; onchange cũng chép usage cho form. Không có constraint unique invoice_month theo phòng.

### Trạng thái: đọc đúng thứ tự điều kiện

`_auto_update_status(force_pending=False)` xét từng invoice theo đúng thứ tự:

| Thứ tự | Điều kiện | Kết quả |
| --- | --- | --- |
| 1 | status hiện tại `canceled` | Bỏ qua, giữ canceled |
| 2 | total <= 0 và chưa trả | draft |
| 3 | remaining <= 0 và total khác 0 | paid |
| 4 | force_pending, hoặc không còn draft, hoặc đã trả một phần; due_date < hôm nay | overdue |
| 5 | Cùng điều kiện kích hoạt dòng 4, chưa quá hạn và paid > 0 | partially_paid |
| 6 | Cùng điều kiện kích hoạt dòng 4, chưa quá hạn và paid = 0 | pending |
| 7 | Không khớp | Giữ nguyên trạng thái |

Quá hạn có ưu tiên hơn thanh toán một phần. Draft chưa trả vẫn giữ draft cho đến xác nhận/force_pending; reset tiền đã trả từ paid chuyển về pending hoặc overdue theo hạn. Canceled giữ nguyên.

Actions: `action_confirm()` chỉ xử lý draft, yêu cầu total > 0 rồi đặt pending và auto status theo hạn; `action_paid()` khóa row hóa đơn, từ chối canceled, đặt paid_amount = total; `action_cancel()` đặt canceled. Các lệnh paid/pay/unpaid khóa row và refresh cache trước khi thay đổi để tránh mất cập nhật đồng thời.

`write()` kiểm tra set `_locked_after_draft_fields` trước khi ghi. Set gồm phòng, tháng, ngày, hạn, reading, rent, điện/nước usage và giá, utilities, phí khác, discount. Đổi status cùng lúc không bỏ qua kiểm tra trạng thái cũ. Paid_amount, notes, status không thuộc set khóa. Không có override invoice unlink để cấm xóa theo trạng thái.

Validation ngày: due_date không trước invoice_date (bằng nhau được phép). Tháng parse bằng datetime. Validation không âm kiểm tra rent, giá/usage điện/nước, utilities, other_charges, discount, paid_amount. ORM chặn discount > subtotal và paid_amount > total; không hỗ trợ trả dư.

## 7. Telegram: giao thức và flow

### Menu, nhắc hạn, cảnh báo và tổng kết (19.0.1.3.1)

- Sau khi xác nhận ghi chỉ số bằng menu, bot hiện nút **Tạo hóa đơn** cho đúng reading vừa lưu. Bấm nút, nhập kỳ MM/YYYY rồi Xác nhận mới tạo hóa đơn; Hủy không tạo. Hóa đơn mới có tổng > 0 tự xác nhận như /inv; nếu reading đã có hóa đơn cùng kỳ thì trả hóa đơn đó, không tạo trùng hoặc đổi trạng thái; khác kỳ phải dùng menu Đổi kỳ hóa đơn. Nút chỉ áp dụng trong phiên vừa ghi, hết hạn hoặc /menu sẽ bỏ lựa chọn này.
- `/start` hoặc `/menu` hiện reply keyboard: Ghi chỉ số, Hóa đơn, Thanh toán, Tổng kết tháng, Đổi kỳ hóa đơn, Sửa ngày chỉ số, Hủy. Menu dùng text messages, không callback_query; không cần thay allowed_updates. Chỉ xử lý menu sau khi chat đã được cấp quyền. Session nội bộ khóa theo hash bot token/chat ID/from user ID, hết hạn sau 30 phút không hoạt động; mỗi user trong group có phiên riêng. `/cancel`/Hủy bỏ phiên nhập; slash command khác cũng xóa phiên đang nhập để tránh xác nhận nhầm. Dữ liệu phiên gồm lựa chọn/numeric/date, không lưu raw message.
- Ghi chỉ số: chọn phòng (tối đa 30 nút hoặc nhập mã) → điện → nước → ngày/Hôm nay → preview/cảnh báo → Xác nhận. Chưa xác nhận thì chưa create/write reading. Ngày/số và regression được validate; confirm gọi upsert hiện có, chặn reading đã có invoice. Sau thành công, phiên giữ reading để chọn Tạo hóa đơn; receipt ngăn duplicate confirmation. Kỳ thay công tơ/manual tiếp tục nhập trong backend.
- Hóa đơn: chọn phòng → tối đa 10 invoice không canceled → chọn số để xem chi tiết. Thanh toán: chọn tối đa 20 invoice không draft/paid/canceled → nhập số tiền VND → Xác nhận. Chỉ confirm mới gọi handler pay hiện có; validation overpayment/canceled vẫn áp dụng. Các menu không thay đổi mô hình paid_amount hoặc cọc.
- Tổng kết: menu chọn phòng/tháng hoặc `/summary MM/YYYY [mã_phòng]`; bỏ mã để xem tất cả phòng. Backend Báo Cáo → Tổng Kết Tháng dùng transient room.monthly.summary, không tạo bảng snapshot tài chính. Theo invoice_period_date và expense_date, loại invoice draft/canceled; gồm rent/điện/nước/utilities/other/discount và chi phí phát sinh độc lập. Tổng cost = tổng invoice.total_amount + expenses. So sánh chênh lệch VND với tháng trước. paid/remaining là số hiện tại trên invoice kỳ được chọn, không phải dòng tiền theo ngày trả (chưa có payment ledger). Không gồm tiền cọc.
- Cảnh báo: anomaly_warning non-stored trên reading, hiện trong form và Telegram success/preview. Mặc định tăng >50% so với mức trung bình có trọng số ngày (tổng usage/tổng ngày) của tối đa 3 interval lịch sử gần nhất; cần ít nhất 2 interval hợp lệ dài từ 7 ngày. Chuỗi số cũ phải khớp số hiện tại của reading trước để so sánh; chuỗi không khớp bị bỏ qua. Hai lần ghi hiện tại cách dưới 7 ngày chỉ hiện thông báo chưa đủ khoảng thời gian so sánh và gợi ý dùng ngày đo thực tế, không hiện phần trăm tăng. Usage quy đổi theo số ngày giữa hai reading; không so kỳ replaced/manual hoặc baseline 0. Chỉ cảnh báo, không chặn lưu. Đổi ngưỡng qua Settings; thay lịch sử/param cần reload để lấy compute mới.
- Nhắc hạn: opt-in telegram_reminders_enabled (mặc định tắt), reminder_days mặc định 3. Cron status hiện có gọi room.telegram.reminder._run_reminders; giữ todo activity và sửa activity_schedule dùng activity_type_id cho Odoo 19. Chỉ invoice không draft/paid/canceled, remaining>0, có due_date. Gửi một lần upcoming khi vào cửa sổ, một lần overdue sau hạn cho mỗi bot_key/invoice/chat/due_date; không gửi hàng ngày. Nếu đổi hạn hoặc đổi bot token sẽ có key mới. bot_key là SHA-256 của token, không lưu token trong delivery. Cron chỉ gửi pending thuộc bot hiện tại; không phát pending bot cũ qua bot mới. Migration 19.0.1.3.1 gán delivery legacy cho hash token đang cấu hình và giữ state để không gửi lại trên cùng bot sau upgrade; chưa thể suy ra bot cũ nếu token đã đổi trước upgrade. Mọi chat trong allowlist nhận nhắc (không có mapping ownership phòng). Delivery pending/sent/skipped, unique key và advisory lock chống trùng các lần cron thông thường; failure/API ok false retry lần cron sau. Trước gửi kiểm tra lại status/còn lại/hạn/chat. Token/allowlist trống hoặc setting tắt thì không gửi. Network gửi thành công nhưng process chết trước DB commit vẫn có thể gửi trùng lần sau; chưa có exactly-once giao tiếp ngoài DB.
- Scheduler local vẫn max_cron_threads=0: để nhắc tự động cần chạy Odoo với --max-cron-threads=1 và bật Nhắc hạn Telegram trong Settings rồi Save. Code không tự đổi config, không tự kích hoạt bot thật.

Models session/reminder chỉ cấp read cho base.group_system, mutation nội bộ sudo. Monthly summary cấp CRUD transient cho base.group_user. Python files mới import qua models/__init__.py, view summary được manifest load trước menu.

### Inbound controller

`controllers/telegram_webhook.py` khai báo POST `/room_rental_expense/telegram/webhook`, `type='http'`, `auth='public'`, `csrf=False`.

1. Đọc JSON bằng `get_json(silent=True) or {}`; dùng parameter sudo.
2. Lấy secret từ header `X-Telegram-Bot-Api-Secret-Token`, fallback `kwargs.get('secret')` (query/form parameter của route). Không đọc `payload['secret']` từ JSON để xác thực.
3. Secret chưa cấu hình hoặc không khớp đều trả HTTP 403: `{"ok":false,"error":"invalid_secret"}`. Allowlist chưa cấu hình trả 403 `allowed_chats_not_configured`, ngoại trừ `/connect <mã>` để ghép nối chat; pairing vẫn bắt buộc secret và mã hợp lệ.
4. Chỉ nhận `message`; bỏ qua edited_message và update không có message với HTTP 200 ignored. JSON không phải object, message không phải object hoặc update_id không phải integer không âm thì trả 400 `invalid_update`.
5. Gọi `room.telegram.update.sudo()._process_update(payload)`: advisory transaction lock theo bot/update_id; receipt đã có thì trả HTTP 200 duplicate/ignored, không chạy lại handler và không gửi lại reply. Receipt mới và nghiệp vụ commit cùng transaction; thay bot token tạo namespace khác. Receipt chưa có chính sách tự dọn (cần giữ để chống replay).
6. Gửi message kết quả qua Bot API `sendMessage`, rồi trả result JSON HTTP 200.

Outbound reply sendMessage POST JSON gồm `chat_id`, `text` và `reply_markup` khi dùng menu, timeout 10 giây. Thiếu token/chat/text thì bỏ qua gửi. `URLError` được log và không cố ý rollback nghiệp vụ. Không có retry/queue, không kiểm tra body `ok` của sendMessage, không chia tin dài.

### Sửa ngày đo của chỉ số nhập muộn

Menu **Sửa ngày chỉ số** lọc hóa đơn không hủy có reading trước khi giới hạn 20 record mới nhất, rồi chọn hóa đơn (hoặc nhập số invoice), nhập ngày đo thực tế YYYY-MM-DD → lý do 1–500 ký tự → preview → Xác nhận. Áp dụng cả hóa đơn đã trả tiền. `_correct_reading_date` chỉ sửa reading_date bằng ORM tầng cha; write thông thường vẫn khóa reading đã gắn invoice. Khóa phòng/invoice/reading, kiểm tra reading liền trước/sau theo ngày đích. Với công tơ không thay: số current đảo chiều so với bản trước/sau chỉ là cảnh báo có số cụ thể và ngày liên quan trong preview, không chặn sửa ngày. Cho phép sửa từng bản ghi lịch sử nhập muộn khi các bản còn lại chưa được sửa ngày. Chênh lệch số previous đã chốt với current của bản liền kề là lưu ý ở preview, không chặn đổi ngày; cho phép dữ liệu nhập muộn/thiếu kỳ mà vẫn giữ usage và tiền đã chốt. Bản đang sửa thay công tơ bỏ kiểm tra liên tục phía trước; bản sau thay công tơ bỏ kiểm tra phía sau. Không tự sửa tiền/chỉ số của bản lân cận; user cần đối chiếu/sửa các ngày lịch sử trước khi ghi lần đo mới. Đổi ngày không kiểm tra invoice_date. Từ chối ngày tương lai, ngày trùng reading khác cùng phòng, invoice hủy, reading không còn link hoặc ngày/link đã đổi so với preview. Chatter invoice ghi ngày cũ/mới và lý do. Giữ nguyên số cũ/mới, usage, số tiền, kỳ/ngày lập/hạn và thanh toán của invoice; không tự tính lại các reading lịch sử hoặc hóa đơn. Việc sửa ngày ảnh hưởng thứ tự lịch sử, cảnh báo theo ngày và số cũ gợi ý cho lần ghi mới. Không tự suy luận ngày cuối tháng từ kỳ invoice; user phải cung cấp ngày đo thật. Sau sửa bản ghi cũ về ngày tháng 5, ngày 07/10 có thể ghi bản mới; số trước vẫn là reading gần nhất có ngày nhỏ hơn 07/10. Nếu đã có các reading sau ngày tháng 5, các số cũ của chúng không tự được cập nhật. Lỗi upsert bản ghi đã có invoice nêu đúng ngày, số hóa đơn, kỳ và menu sửa ngày, không gọi nhầm là khóa cả tháng.

### Kỳ tính tiền và đổi kỳ

Kỳ hóa đơn độc lập với ngày ghi chỉ số và ngày lập. Ví dụ reading ngày 01/10/2026 có thể tính cho kỳ 09/2026. Menu Tạo hóa đơn hỏi kỳ MM/YYYY, ngày lập là hôm nay; backend có thể sửa kỳ trên invoice nháp. Các luồng cũ UI tạo từ reading và /inv vẫn gợi ý kỳ theo tháng ghi, không tự suy luận tháng trước. Menu tạo mới chặn phòng đã có invoice không hủy cùng kỳ; kiểm tra lại khi xác nhận và khóa phòng trong transaction. Đây là guard của menu, chưa phải constraint toàn cục cho ORM/import/slash command.

Menu **Đổi kỳ hóa đơn** hiển thị tối đa 20 hóa đơn mới nhất đủ điều kiện, cả trong tin nhắn và reply keyboard, label số hóa đơn | tên phòng | kỳ. Nếu không có, bot thông báo rõ không có hóa đơn để đổi kỳ. Có thể nhập số hóa đơn ngoài danh sách; server vẫn kiểm tra điều kiện. Flow: chọn/nhập số invoice → nhập kỳ → nhập lý do 1–500 ký tự → preview kỳ cũ/mới/lý do → Xác nhận. Cho phép nháp, pending, overdue, partially_paid và paid; chỉ chặn canceled. Không đưa về nháp hoặc xác nhận lại. Giữ nguyên trạng thái, paid_amount và remaining_amount kể cả thanh toán phát sinh sau preview; row lock serialize với payment. Preview báo tổng kết tháng sẽ thay đổi. Chặn kỳ đích đã có invoice không hủy của phòng; canceled không chiếm kỳ. Preview cũ bị từ chối nếu kỳ đã thay đổi. Giữ nguyên số tiền, giá áp dụng, ngày lập, hạn trả và ngày reading; đổi kỳ chỉ sửa phân loại báo cáo, không tính lại giá. Tracking/chatter lưu kỳ cũ → mới và lý do sửa. Không tự sửa dữ liệu lịch sử. Hủy/hết hạn không đổi kỳ.

### Command và cú pháp

| Lệnh | Hành vi |
| --- | --- |
| `/connect <mã>` | Ghép nối chat riêng bằng mã một lần, hết hạn 10 phút, do admin tạo trong Settings |
| `/help` | Trả danh sách lệnh |
| `/start`, `/menu` | Mở menu nhập theo bước cho chat đã cấp quyền |
| `/cancel` | Hủy phiên nhập hiện tại |
| `/summary MM/YYYY [mã_phòng]` | Tổng kết tháng, tất cả phòng nếu bỏ mã phòng |
| `/reading P101 350 28 [YYYY-MM-DD]` | Ghi/cập nhật chỉ số điện, nước; không có ngày thì hôm nay |
| `/reading room:P101 elec:350 water:28 [date:YYYY-MM-DD]` | Cùng nghiệp vụ theo format key:value, giữ thứ tự này |
| `/inv P101 YYYY-MM-DD` | Tìm reading đúng ngày; lấy invoice đã có hoặc tạo mới rồi confirm nếu total > 0 |
| `/show INV-2026-0001` | Chi tiết invoice và manual_breakdown |
| `/invoices P101` | Tối đa 10 invoice, sort kỳ/ngày/id giảm dần, gồm cả canceled |
| `/readings P101` | Tối đa 10 reading, sort ngày/id giảm dần |
| `/paid INV-2026-0001` | Ghi đã trả đủ bằng action_paid |
| `/pay INV-2026-0001 1000000` | Cộng số tiền > 0, từ chối nếu vượt total_amount hoặc canceled, cập nhật status force_pending |
| `/unpaid INV-2026-0001` | Reset paid_amount = 0 rồi cập nhật status force_pending |

Slash dispatcher so sánh uppercase nên tên lệnh nghiệp vụ không phân biệt hoa thường; mã phòng và số invoice search '=' giữ nguyên chuỗi. Menu hỗ trợ /start, /menu, /cancel; chưa normalize command@botname, callback query, ảnh/OCR, hoặc thay công tơ/manual override qua Telegram.

Parser reading dùng fullmatch, số không âm, chấp nhận dấu `.` hoặc `,` làm thập phân; room key một token không chứa khoảng trắng. `_parse_telegram_amount()` xóa mọi dấu `.` và `,` rồi float: `1.000.000` → 1000000; `1,5` → 15, không phải 1.5.

### Tìm phòng và upsert

Room lookup là domain OR trên ba field, limit 2: không có → lỗi; >1 → lỗi “mã phòng bị trùng”, kể cả một record khớp telegram_code và record khác khớp room_number/name. `telegram_code` duy nhất vẫn không loại trừ sự trùng chéo này. Khi xây ví dụ command trả về, bot ưu tiên reference telegram_code → room_number không chứa space → name không chứa space.

Upsert đọc `(room_id,reading_date)` chính xác, lấy record mới nhất khi có nhiều bản ghi trùng. Luôn chuẩn bị số trước, preview bằng `new(vals)` rồi kiểm tra regression. Existing có invoice thì lỗi; chưa có invoice thì write; không tìm thấy thì create. Không có SQL unique cho key upsert, không có khóa chống race.

`process_telegram_message()` lấy text, xử lý trong savepoint và bắt **ValidationError** để trả `status:error`; lỗi nghiệp vụ rollback handler. `/connect` kiểm tra mã và chat riêng trước allowlist; menu kiểm tra allowlist chat ID rồi xử lý session; slash command nghiệp vụ kiểm tra allowlist rồi dispatch. Allowlist CSV so sánh `str(chat.id)`, không kiểm tra ownership phòng. Rỗng allowlist từ chối lệnh nghiệp vụ. Exception loại khác rollback request và có thể thành lỗi HTTP ngoài schema result thông thường.

### Kết quả và idempotency

Success dùng `status:'success'`, `message`, tùy command có `reading_id`, `invoice_id`, `action:'created'/'updated'`. Validation error dùng `status:'error'`, `message`; cả hai thường HTTP 200. Không suy luận tất cả response có `ok:true`.

Tin reading thành công có phòng, reference, ngày/tháng, số cũ → mới và usage, gợi ý `/inv`. Invoice summary có status key tiếng Anh, tiền phòng/điện/nước/tiện ích/phí/giảm/tổng/đã trả/còn lại, khối “Chi tiết”, gợi ý paid/pay. Payment summary có status/đã trả/còn lại. Tiền format dấu chấm nghìn, 0 chữ số thập phân.

Webhook deduplicate `update_id`; edited_message không chạy lệnh. Hai message mới có update_id khác nhau vẫn là hai khoản trả riêng. `/inv` dùng invoice đã gắn để tránh tạo lại trên cùng reading. `/unpaid` reset tiền và trạng thái về pending/overdue; paid/pay/unpaid từ chối canceled. Lỗi nghiệp vụ đã trả HTTP 200 cũng được lưu receipt; muốn thử lại sau khi sửa đầu vào cần gửi message mới.

### Settings và setup

Bảy config_parameter field: telegram_bot_token, telegram_webhook_secret, telegram_allowed_chat_ids, telegram_public_url, telegram_reminders_enabled, reminder_days và usage_alert_percent. UI Settings giới hạn `base.group_system`; mọi action cũng kiểm tra admin ở server. Giao diện thêm khối Nhắc hạn và cảnh báo tiêu thụ bên cạnh bốn khối setup: Kết nối bot, Ghép nối chat, Trạng thái kết nối, Cấu hình nâng cao (details thu gọn). Label nằm trên input rộng; token/secret hiển thị password. Mã ghép nối và thông tin kết nối readonly trên transient settings. Chat đã cấp quyền readonly trong khối ghép nối, sửa thủ công trong nâng cao. Notification thành công tự đóng; warning giữ đến khi đóng; chi tiết/mã nằm trong form thay vì toast dài. Notification có next action mở lại đúng transient record và tab module để cập nhật field từ server.

`action_register_telegram_commands()` gọi setMyCommands với 13 lệnh (gồm connect/menu/cancel/summary), không setWebhook hoặc lưu cấu hình. Bot API dùng helper `_telegram_api`, timeout 15 giây, HTTP/network/JSON/API errors thành UserError chung không lộ token. Các endpoint dựa trên [Telegram Bot API chính thức](https://core.telegram.org/bots/api#setwebhook); menu dùng [ReplyKeyboardMarkup](https://core.telegram.org/bots/api#replykeyboardmarkup).

Luồng setup nhanh đã triển khai:

1. Nhập Bot Token và URL HTTPS public của Odoo/tunnel trong Settings. URL không có userinfo/query/fragment; nhận base URL hoặc full route webhook.
2. Bấm **Kết nối Telegram** (`action_connect_telegram`): tạo secret nếu trống, kiểm tra charset chữ/số/_/- và dài 1–256; setWebhook với allowed_updates=['message'], không drop update đang chờ. Thành công thì lưu token/secret/URL; giữ allowlist đã lưu khi field chat trống; tạo mã và đăng ký gợi ý lệnh. Nếu setMyCommands lỗi sau khi webhook thành công, giữ cấu hình và thông báo warning để đăng ký lệnh lại. Timeout setWebhook có thể có trạng thái remote chưa xác định, cần kiểm tra rồi thử lại.
3. Copy `/connect <mã>` hiển thị và gửi trong chat riêng với bot trong 10 phút. Mã random 192 bit, dùng một lần; system parameters chỉ lưu hash SHA-256, hash token bot và expiry. Advisory transaction lock serialize tạo/consume mã. Mã mới hoặc đổi bot token vô hiệu mã cũ. Chat phải private, ID integer dương và from.id khớp chat.id; ghép thành công thêm ID vào allowlist, giữ chat đã cấp quyền trước đó. Pairing rollback savepoint khi lỗi và dùng receipt chống replay.
4. Bot xác nhận xong, tải lại Settings hoặc bấm **Kiểm tra kết nối** trước khi Save để refresh Allowed Chat IDs. Nút kiểm tra gọi getWebhookInfo, hiển thị URL/pending_update_count/last_error_message, cảnh báo URL chưa khớp Settings. URL khớp chưa chứng minh Telegram đã gọi tới Odoo thành công.
5. **Tạo mã ghép nối** cấp thêm mã cho chat riêng khác. Group vẫn cấu hình Chat IDs thủ công. Khi tunnel đổi URL, nhập URL mới và bấm Kết nối lại.
6. **Ngắt kết nối** gọi deleteWebhook không drop updates, yêu cầu token khớp bot đã lưu; xóa secret/mã pending để endpoint từ chối request mới, giữ token/URL/allowlist cho lần sau.

Setup thủ công vẫn được hỗ trợ như bên dưới; luồng Settings ở trên không cần tự gọi curl/getUpdates hoặc nhập secret/chat ID. Chuẩn bị telegram_code, tiền thuê/config giá cho phòng rồi test `/help`, reading, inv, show.

#### Thiết lập Telegram thủ công (tùy chọn)

1. Trong BotFather gửi `/newbot`, nhập tên và username kết thúc bằng `bot`, lấy token. Lưu token trong Settings hoặc `Settings -> Technical -> Parameters -> System Parameters`.
2. Với bot test, nếu đã có webhook, gọi `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook`; thao tác này ngắt webhook đang dùng của bot đó.
3. Mở chat, bấm Start hoặc gửi `/start` để tạo update. Gọi `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`, lấy `result[].message.chat.id`. Khi webhook đang bật không dùng getUpdates. Chat cá nhân thường ID dương; group/supergroup ID âm. Dùng chat.id, không dùng username hoặc from.id.
4. Lưu token, secret tự chọn và allowlist chat IDs ngăn cách bằng dấu phẩy. Chuẩn bị phòng, ví dụ telegram_code `P101`, room_number `101`, default_rent `3500000` và cấu hình giá phù hợp.
5. Chạy Odoo, tạo tunnel HTTPS đến port thực tế, ví dụ `ngrok http 1369` cho cấu hình local này. URL webhook là `https://<public-domain>/room_rental_expense/telegram/webhook`. Mở route bằng browser GET không phải cách kiểm thử POST.
6. Gọi `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<public-domain>/room_rental_expense/telegram/webhook&secret_token=<YOUR_SECRET>`, rồi `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo`. Các URL là mẫu cần thay placeholder; không lưu URL chứa token thật vào tài liệu/log dùng chung.
7. Kiểm tra getWebhookInfo có `ok=true`, `result.url` đúng và không có last_error_message. Secret sai thường gây 403; timeout có thể do tunnel tắt/domain không public/proxy sai; SSL error cần kiểm tra HTTPS/certificate.
8. Trong Settings bấm “Đăng ký lệnh Telegram”. Test `/help`, `/reading P101 350 28 2026-10-06`, `/inv P101 2026-10-06`, `/show <invoice_number>`. Nếu tunnel đổi URL phải setWebhook lại. Nếu bot im lặng, kiểm tra token, URL, tunnel, outbound và allowlist; nếu không tìm thấy phòng, kiểm tra mã khớp chính xác và không trùng chéo.

Template system parameters (điền giá trị trong Odoo, không điền secrets thật vào file này):

```text
room_rental_expense.telegram_bot_token =
room_rental_expense.telegram_webhook_secret =
room_rental_expense.telegram_allowed_chat_ids =
room_rental_expense.telegram_public_url =
room_rental_expense.default_electric_price =
room_rental_expense.default_water_price =
room_rental_expense.default_wifi_price =
room_rental_expense.default_trash_fee =
room_rental_expense.default_parking_fee =
room_rental_expense.default_other_utilities_price =
room_rental_expense.reminder_days =
```

Master data phòng cần chuẩn bị: name, room_number, telegram_code, default_rent, landlord_name, landlord_phone. Với room.config: room_id, effective_date, electric_price, water_price, wifi_price, trash_fee, parking_fee, other_utilities_price, notes.

## 8. Giao diện, widget và PDF

Root menu `room_rental_menu`: “Quản Lý Phòng Trọ”, icon `room_rental_expense,static/description/room_icon.png`.

| Nhóm menu | Màn hình |
| --- | --- |
| Quản Lý | Phòng Trọ, Chỉ Số Công Tơ, Hóa Đơn |
| Chi Phí & Khác | Chi Phí, Tiền Cọc, Sự Cố |
| Cấu Hình | Giá Tiện Ích, Lịch Sử Phòng |
| Báo Cáo | Hóa Đơn, Chi Phí (actions pivot,graph,list) |

Phòng mở `kanban,list,form`; kanban có tài chính, ảnh, chủ phòng, count, thời gian thuê. Badge “Sắp hết hạn” chỉ kiểm tra có end_date, không tính khoảng cách đến ngày hết hạn. Form có notebook các quan hệ và chatter. Nút xem hóa đơn/chỉ số từ phòng và XML dùng `view_mode='list,form'`.

Reading form có tổng quan, tab điện/nước, cờ thay, nhập tay, ảnh, tạo/mở hóa đơn. Readonly XML không hoàn toàn giống set khóa Python (ví dụ replacement_last), nên guard server vẫn là nguồn quyết định cuối.

Invoice form có confirm/paid/cancel/PDF, statusbar, chi tiết và ghi chú, paid_amount vẫn editable. Action invoice chính lọc `status != canceled`; không có nghĩa dữ liệu hủy biến mất khỏi totals/report/Telegram. Search invoice có nhóm phòng/tháng/status, lọc hạn/overdue/nháp/đã trả; search reading nhóm phòng/tháng, lọc thay; expense nhóm phòng/category. Không khai báo riêng pivot/graph view trong addon, report action sử dụng view mặc định Odoo.

`currency_widget.js` đăng ký:

- `vnd_currency`: subclass FloatField; Math.round, dấu chấm phân nghìn, hậu tố ` ₫`.
- `number_format`: subclass FloatField; integer phân nghìn, decimal tối đa 2 chữ số rồi trim; cách dùng cùng dấu chấm có thể gây mơ hồ giữa nghìn/thập phân.
- `window.formatVND` helper global. Format chỉ hiển thị; không đổi kiểu trường hoặc quy tắc tính tiền.
- Kanban dùng các field Python `*_fmt`, không gọi widget để format trực tiếp.

`reports/invoice_template.xml`: QWeb `report_room_invoice` gọi `web.external_layout`, loop docs, hiển thị phòng, kỳ, ngày/hạn, bảng tiền, đã trả/còn lại, manual_breakdown, notes. Action `report_room_invoice_pdf` khai báo bằng record `ir.actions.report`, binding model room.invoice, type qweb-pdf; tên file `Invoice - <invoice_number>`. Template dùng t-esc giá trị tiền trực tiếp, không dùng widget VND. `action_print_invoice()` trả False nếu không tìm được XML ID report. Admin chưa có layout công ty có thể nhận action cấu hình layout trước khi in. Tests render QWeb HTML; chưa kiểm tra PDF bằng wkhtmltopdf.

## 9. Cron và reminder

`data/cron_data.xml` tạo `cron_room_invoice_status_update`, name “Room Invoice Status Update”, interval 1 ngày, active, gọi `model.cron_update_overdue_status()`.

Method đọc reminder_days, parse int (ValueError fallback 3). Tìm invoice không paid/canceled, có due_date < today rồi gọi bảng auto status; partial chuyển overdue, draft chưa trả vẫn giữ draft.

Tìm invoice draft/pending/partial với due_date từ hôm nay đến hôm nay + reminder_days, tạo todo activity nếu chưa có cùng activity type và summary “Nhắc thanh toán hóa đơn”. Deadline = due_date, note gồm số/hạn/còn lại. Sau đó chạy nhắc Telegram opt-in như phần 7. Không có email template riêng hoặc tự close reminder activity khi đã thanh toán.

Cron record active vẫn cần scheduler instance chạy. Local `max_cron_threads=0` tắt cron threads; muốn kiểm chứng phải chạy thủ công hoặc điều chỉnh config môi trường kiểm thử.

## 10. Cấu hình, chạy và upgrade

### System parameters

Tất cả key có prefix `room_rental_expense.`. XML `data/room_config_data.xml` tạo mặc định với `noupdate=1`:

| Hậu tố key | Giá trị ban đầu | Dùng ở |
| --- | --- | --- |
| `default_electric_price` | 3500 | Giá fallback/kWh |
| `default_water_price` | 15000 | Giá fallback/m³ |
| `default_wifi_price` | 150000 | Utilities fallback/tháng |
| `default_trash_fee` | 30000 | Utilities fallback/tháng |
| `default_parking_fee` | 0 | Utilities fallback/tháng |
| `default_other_utilities_price` | 0 | Utilities fallback/tháng |
| `reminder_days` | 3 | Cửa sổ nhắc trước hạn |
| `telegram_bot_token` | rỗng | sendMessage/setMyCommands |
| `telegram_webhook_secret` | rỗng | Bắt buộc để nhận webhook; thiếu/sai trả 403 |
| `telegram_allowed_chat_ids` | rỗng | CSV chat.id bắt buộc; rỗng từ chối |

Giá fallback float parse lỗi → 0. `noupdate=1` cũng áp dụng sequence và cron: upgrade module thường giữ dữ liệu đã cấu hình thay vì ghi lại XML defaults. Giá thực tế lấy từ DB, không mặc định luôn bằng bảng này.

`telegram_public_url` được lưu qua Settings, không có default trong XML. Các parameters nội bộ `telegram_pairing_hash`, `telegram_pairing_bot`, `telegram_pairing_expiry` dùng cho mã ghép nối; không cần nhập tay hoặc đưa giá trị thật vào tài liệu.

### Local instance

`config/local.conf`: PostgreSQL localhost:5432, user lamnv, db room_rental_dev; http_enable True, http_interface 0.0.0.0, http_port 1369; workers 0, max_cron_threads 0, limit_time_real 12000, limit_memory_hard 0 (không đặt hard limit), log_level info, proxy_mode False. Có admin_passwd và db_password; không copy giá trị vào prompt/file context. Đã thay xmlrpc/xmlrpc_interface/xmlrpc_port bằng http_enable/http_interface/http_port; bỏ các option core Odoo 19 không nhận logrotate/secret_key/server_environment. Kiểm tra config bằng runtime Odoo 19 với --version ngày 2026-10-06 không còn warning cấu hình.

addons_path gồm `project`, `/home/lamnv/code/odoo-19/odoo/addons`, `/home/lamnv/code/odoo-19/addons`, `addons_oca/addons_oca/web`, `~/code/learn_odoo`; đã kiểm tra các thư mục core tồn tại. local.conf được Git ignore và chứa secrets; thay đổi cấu hình chỉ ở local.

Không có script khởi động/venv/requirements riêng của addon nghiệp vụ trong workspace. Dưới đây là **mẫu lệnh**, giả định chạy từ root workspace trong Linux/WSL, Python environment Odoo đã chuẩn bị và `../odoo/odoo-bin` thật sự tồn tại:

```bash
# Chạy local
python ../odoo/odoo-bin -c config/local.conf

# Cài vào database dev riêng, khi chưa cài module
python ../odoo/odoo-bin -c config/local.conf -d <dev_db> \
  -i room_rental_expense --stop-after-init

# Upgrade module đã cài
python ../odoo/odoo-bin -c config/local.conf -d <dev_db> \
  -u room_rental_expense --stop-after-init
```

Không tự chạy cài/upgrade trên DB thật để đọc tài liệu. Khi deploy: backup DB + filestore, bảo đảm OCA dependency đúng branch, upgrade trong staging, kiểm tra assets/view/report/cron/Telegram, rồi mới áp môi trường thật. Local tunnel phải trỏ port instance thực tế (config này dự kiến 1369), không mặc định mọi instance là 8069.

## 11. Các addon OCA có trong source

Thư mục gốc OCA: `addons_oca/addons_oca/web`. Có manifest, pyproject, docs/readme, bản dịch, ảnh, tests và cấu hình lint riêng. License từng addon có LGPL-3 hoặc AGPL-3, không áp license custom module cho cả bộ.

Bộ OCA được quản lý bằng Git submodule từ `https://github.com/OCA/web.git`, ghim commit `3ad4c97ee29eda9f6278acba4cba09243e064a22` trong lần thiết lập này. `.gitmodules` nằm ở gốc Git repository (thư mục cha của workspace). Sau khi clone repository, chạy `git submodule update --init --recursive -- lamnv_utils/addons_oca/addons_oca/web` từ gốc repository để lấy OCA; khi đổi phiên bản OCA, commit cả con trỏ submodule mới và cập nhật context. Không cần commit thư mục `.git` hoặc cache Python của OCA. Repository còn có gitlink `odoo` tồn tại từ trước nhưng thiếu mapping trong `.gitmodules`; lệnh submodule toàn repo có thể lỗi, nên dùng đường dẫn OCA cụ thể. Runtime Odoo cần được chuẩn bị riêng; chưa có đủ dữ liệu để khôi phục mapping đó.

| Addon | Vai trò / điểm vào chính |
| --- | --- |
| **`web_responsive`** | Dependency trực tiếp. Models res.users/ir.http đưa search type/theme vào session; components apps_menu/apps_menu_tools resolve web_icon; canonical/Fuse/command_palette search; responsive layout, chatter/file viewer/control panel/form; tests Python và QUnit |
| **`web_tree_many2one_clickable`** | Dependency trực tiếp. Patch ListRenderer, template thêm nút mở Many2one khi có value và không no_open, hover mới hiện nút; action mở form liên quan |
| **`web_group_expand`** | Dependency trực tiếp. Patch ListController expand/collapse theo tầng nhóm, tạm đổi MAX_NUMBER_OPENED_GROUPS; template nút khi grouped |
| `web_calendar_slot_duration` | Patch calendar renderer/model theo context calendar_slot_duration; data chỉnh action Scheduled Actions |
| `web_dark_mode` | User/user settings dark_mode/device dependent, ir.http chọn color scheme/cookie, service JS chuyển theme và SCSS dark; loại trừ web_enterprise |
| `web_dialog_size` | Patch Dialog/SelectCreateDialog, nút maximize/restore, localStorage; parameter web_dialog_size.default_maximize |
| `web_environment_ribbon` | Abstract model trả ribbon.name/color/background; tên hỗ trợ {db_name}; component render ribbon góc màn hình |
| `web_favicon` | res.company favicon, template web.layout, chọn icon theo website/current company cookie |
| `web_ir_actions_act_window_message` | Model/action handler ir.actions.act_window.message, dialog text/HTML, buttons gọi ORM hoặc mở action |
| `web_m2x_options` | Config/session và patches Many2one/Many2many: create/create_edit/open/limit/field_limit_entries, màu autocomplete |
| `web_pwa_customize` | Settings tên/màu/icon PWA, attachment SVG/PNG, controller manifest; tests icon/manifest |
| `web_refresher` | Patch ControlPanel, nút refresh pager/search/action, animation |
| `web_remember_tree_column_width` | Patch ListRenderer lưu width localStorage theo model/field |
| `web_search_with_and` | Patch SearchModel/SearchBar cho AND search |
| `web_widget_bokeh_chart` | Widgets bokeh_chart/bokeh_chart_json, load Bokeh JS 3.9.0, render script/div; Python external dependency bokeh==3.9.0 |

`addons_oca/.../requirements.txt` chứa `bokeh==3.9.0` sinh từ manifest external_dependencies của bộ. Module phòng trọ không dùng Bokeh widget, không cần suy luận phải cài Bokeh chỉ để hiểu hoặc sửa nghiệp vụ phòng trọ.

Các dependency này patch thành phần web toàn cục khi được cài: nếu lỗi list/menu/chatter sau upgrade, cần đọc source OCA liên quan cùng custom XML. Ưu tiên sửa nghiệp vụ trong `project/`; thay OCA cần xác định ảnh hưởng toàn instance và giữ bản quyền/license.

## 12. Điểm cần biết và giới hạn hiện tại

Các mục dưới là quan sát từ code, không phải danh sách bug đã tái hiện ở runtime.

1. **Phạm vi cá nhân:** không tenant/contract model, multi-company isolation, payment ledger, đối soát ngân hàng hoặc accounting integration. Một số tên/docs dùng “phải thu”; không vì vậy suy luận đây là hệ thống thu tiền đa người thuê.
2. **Quyền rộng:** ACL cho 8 model nghiệp vụ CRUD đầy đủ với base.group_user; không có record rules custom. Receipt chỉ cấp đọc cho base.group_system, ghi bằng sudo nội bộ. Webhook sudo nhưng secret/allowlist bắt buộc.
3. **Tổng phòng đã loại canceled** ở tổng hóa đơn/đã trả/còn lại; dependency gồm status để cập nhật khi hủy. Vẫn tính draft; history chưa lọc thời gian/hủy; cọc/chi phí không tự vào invoice.
4. **Reading không unique phòng/ngày/tháng**; invoice không unique số/tháng/phòng. Unique mã Telegram, cấu hình phòng/ngày và invoice/reading dùng models.Constraint. Upgrade DB có dữ liệu cũ trùng cần xử lý dữ liệu trước khi cài constraint; không tự xóa dữ liệu trùng.
5. **Đồng bộ liên kết không đối xứng hoàn toàn:** invoice điều khiển sync; ghi trực tiếp reading.invoice_id không chạy chiều ngược. Không tự cascade recalculation kỳ sau khi sửa reading trước.
6. **Status:** partial quá hạn chuyển overdue; unpaid từ paid về pending/overdue. Draft chưa trả hết hạn chưa tự overdue. Actions/commands thanh toán từ chối canceled; write paid_amount trực tiếp vẫn theo ràng buộc tài chính, không bị khóa theo canceled.
7. **Validation tài chính:** đã chặn other_charges âm, discount vượt subtotal, overpayment. Model bổ trợ cọc/chi phí vẫn chưa kiểm tra số âm/ngày.
8. **Create áp giá force** có thể ghi đè giá tay; rent 0 có thể bị thay bằng default_rent. Reprice theo invoice_date, không chỉ theo invoice_month.
9. **Telegram đã dedup update_id**, bỏ qua edited_message, savepoint rollback lỗi nghiệp vụ; chưa normalize command @botname, chia message dài hoặc xử lý file/OCR. Chỉ ValidationError chuyển schema lỗi nghiệp vụ; receipt chưa tự dọn.
10. **UI:** action Python dùng list,form, report dùng record ir.actions.report. Kanban badge chưa thực sự kiểm tra sắp hết hạn; PDF/assets UI cần kiểm tra trực quan riêng.
11. **Local cron tắt**, public tunnel/outbound/token không thể xác nhận từ code. Không có Prometheus/Grafana/APM custom đã triển khai trong addon. Khi theo dõi vận hành, kiểm tra Odoo/proxy logs, webhook 403/5xx, reply failures, lần chạy cron và reminder activities; đây là hướng dẫn, không phải monitoring đã tích hợp.
12. **Tests:** đã thêm TransactionCase/HttpCase riêng và bỏ pattern test_*.py trong .gitignore. Chưa có browser tour, stress test đồng thời, kiểm thử Telegram bot/public tunnel thật.

Không tự sửa các behavior này khi task chỉ yêu cầu viết context. Nếu task sau yêu cầu thay, xác định behavior mong muốn và cập nhật phần context tương ứng.

## 13. Bản đồ sửa code và kiểm chứng

| Yêu cầu | Bắt đầu đọc/sửa | Các nơi liên quan |
| --- | --- | --- |
| Phòng/chủ phòng/tổng | models/rental_room.py | views/rental_room_views.xml, history, totals invoice |
| Giá theo hiệu lực | models/room_config.py, rental_room._get_active_config | room_invoice._apply_config_prices, data/room_config_data.xml |
| Điện/nước/thay công tơ | models/meter_reading.py | views/meter_reading_views.xml, sync invoice, parser Telegram |
| Thêm khoản tiền/đổi công thức | models/room_invoice.py | compute depends, validation, locked set, manual_breakdown, invoice view, report, Telegram summary |
| Trạng thái/thanh toán | room_invoice._auto_update_status và actions | command paid/pay/unpaid, cron domains, status UI, totals |
| Thêm/đổi lệnh Telegram | meter_reading dispatcher/handler/help | settings command payload, controller nếu protocol đổi, phần Telegram và kiểm chứng trong context |
| Token/secret/allowlist | models/res_config_settings.py | views/res_config_settings_views.xml, controller, sender check, defaults/template |
| Cron/nhắc hạn | room_invoice.cron_update_overdue_status | _schedule_reminder_activity, cron_data.xml, reminder_days, local scheduler config |
| PDF | reports/invoice_template.xml | action_print_invoice, manual_breakdown, manifest load |
| Format tiền/số | static/src/js/currency_widget.js | Python formatted fields, XML widgets, Telegram amount format, PDF |
| Menu/icon/list | views/menu_views.xml và view liên quan | room_icon.png, manifest/OCA assets |
| Phân quyền | security/ir.model.access.csv | record rules nếu thêm, controller sudo, ownership nếu thiết kế mới |

Đường dẫn trong bảng tương đối với `project/room_rental_expense/`.

### Kiểm chứng phù hợp

**Sửa ngày độc lập với lịch sử chưa chỉnh xong (2026-10-07):** 76 tests pass, 0 failed/errors, `/tmp/room_rental_date_warning.log`. Kiểm tra bản sau 06/10 còn ngày nhập muộn, bản mới nhất chuyển về 30/07: cảnh báo với ngày/số, vẫn xác nhận được; invoice_date và tiền giữ nguyên. Chuỗi đảo chiều chỉ cảnh báo cho action sửa ngày; guard số mới thấp hơn số trước trong nhập chỉ số thông thường vẫn giữ. Kiểm tra ngày trùng/tương lai/canceled/stale vẫn pass. pycodestyle pass. Quy tắc hiện tại thay guard chặn đảo chiều được thử ở các lần chạy cũ bên dưới.


**Nới guard sửa ngày đúng thứ tự (2026-10-07):** 75 tests pass, 0 failed/errors, `/tmp/room_rental_date_guard_fix.log`. Regression tái hiện bản trước 07/06, bản mới nhất 07/10 chuyển về 30/07, current tăng hợp lý nhưng số previous đã lưu khác bản trước: preview nêu lưu ý, sửa thành công, giữ usage/total/paid/status. Số current đảo chiều vẫn bị chặn. pycodestyle pass; chưa thử bot thật hoặc sửa database người dùng.


**Fix review 19.0.1.3.1 (2026-10-07):** 74 tests pass, 0 failed/errors, log `/tmp/room_rental_review_fixes_final.log`. Regression tests gồm sửa ngày đảo chuỗi điện/sai số cũ nước bị chặn và không đổi tiền; menu sửa ngày vẫn hiện invoice có reading nằm sau 20 invoice không reading; sent/pending phân biệt bot; interval dưới 7 ngày không hiện phần trăm; bỏ qua chuỗi history không khớp. Upgrade từ 19.0.1.3.0 có fixture delivery sent theo schema cũ thực chạy trên DB test: migration giữ state, bot hiện tại không gửi lại, bot mới gửi một lần, unique constraint mới được kiểm chứng qua hai bot cùng invoice/chat/date/kind. Fixture được xóa sau kiểm tra. Logs migration `/tmp/room_rental_fix_migration.log`. pycodestyle pass; không chạy bot thật hoặc nâng cấp database người dùng.


**Sửa ngày chỉ số nhập muộn (2026-10-07):** toàn bộ 67 tests pass, 0 failed/errors, `/tmp/room_rental_correct_date.log`. Test sửa reading ngày hiện tại về tháng 5 trong hóa đơn paid, giữ usage/tiền/paid/status, audit có lý do, sau đó ghi reading mới hôm nay và lấy đúng số trước. Kiểm tra ngày sai/tương lai/trùng và Hủy. pycodestyle pass; bot mock, chưa thử bot thật hoặc sửa database người dùng.


**Sửa kỳ hóa đơn đã thanh toán (2026-10-07):** 65 tests pass, 0 failed/errors, log `/tmp/room_rental_paid_period.log`, database test riêng. Kiểm tra paid xuất hiện trong danh sách và đổi được, lý do rỗng/quá dài bị chặn, paid_amount/remaining/status/ngày giữ nguyên, chatter có lý do, khoản trả phát sinh sau preview giữ nguyên, canceled bị chặn khi chọn và xác nhận. Bot API mock; chưa thử bot thật. Kết quả tests cũ bên dưới mô tả behavior tại lần chạy cũ, quy tắc hiện tại ở phần 7.


**Danh sách chọn đổi kỳ (2026-10-07):** 64 tests pass, 0 failed/errors; `/tmp/room_rental_invoice_choices.log`. Test kiểm tra danh sách rỗng, nhãn số/phòng/kỳ trong tin và keyboard, chọn nhãn đi tiếp tới nhập kỳ. Chưa thử Telegram thật.


**Kỳ hóa đơn độc lập và menu đổi kỳ (2026-10-07):** chạy toàn bộ 63 test methods, 0 failed, 0 errors trên database test riêng; log `/tmp/room_rental_period_final.log`. Bao gồm tạo kỳ khác tháng reading, đổi kỳ giữ tiền/ngày/trạng thái nháp hoặc xác nhận, chatter, tháng sai, hủy, paid/canceled, thanh toán phát sinh sau preview, preview kỳ cũ, invoice trùng xuất hiện khi xác nhận và tổng kết chuyển theo kỳ mới. pycodestyle và kiểm tra giới hạn dòng pass. Bot API mock; chưa thử bot thật hoặc thay đổi dữ liệu database người dùng.


**Nút tạo hóa đơn sau ghi chỉ số (2026-10-07):** thêm tests xác nhận mới tạo, xác nhận lặp không tạo trùng và Hủy không tạo. Chạy lại toàn bộ 56 test methods: 0 failed, 0 errors, log `/tmp/room_rental_menu_invoice.log`; Bot API mock, chưa thử bot thật.


**Kết quả cải tiến 2–5 ngày 2026-10-07 (19.0.1.3.0):** toàn bộ 54 test methods pass, 0 failed, 0 errors trên database test riêng `room_rental_test_20261006`, log `/tmp/room_rental_features_20261007_final.log`. `test_telegram_features.py` kiểm tra menu/xác nhận/hủy/hết hạn/cách ly user, thanh toán vượt số dư và replay, reading đã gắn invoice, cảnh báo có/thiếu lịch sử và khoảng ngày dài, tổng kết lọc trạng thái/phòng/so sánh tháng, nhắc hạn bật/tắt/gửi một lần/chuyển quá hạn/retry/hủy/chat bị thu hồi. HttpCase kiểm tra reply keyboard qua webhook. Sửa lời gọi `activity_schedule(activity_type_id=...)` tương thích Odoo 19. Bot API được mock; chưa kiểm tra browser, bot thật hoặc scheduler chạy liên tục. Không triển khai sổ thanh toán hoặc cải tiến cọc.


Tests nằm trong `project/room_rental_expense/tests/`: test_room_invoice.py (tiền, giá, trạng thái, hủy/tổng, validation, SQL constraints, khóa/link, report HTML), test_meter_reading.py (normal/replacement/manual/regression/previous reading), test_telegram.py (commands, rollback, receipt trùng, ACL, HTTP auth/retry/edited/invalid payload). Các gợi ý bổ sung bên dưới là checklist, không phải kết quả tests đã pass.

**Kết quả cải tiến setup Telegram 2026-10-06 (version 19.0.1.2.0):** test_telegram_setup.py bổ sung connect/setWebhook/setMyCommands, URL/secret invalid, mã đúng/sai/hết hạn/group/reuse/regenerate, kiểm tra/ngắt kết nối, lỗi mạng không lộ token, đăng ký commands lỗi sau setWebhook thành công, reconnect giữ chat, thay bot vô hiệu mã, admin guard. HttpCase test_telegram.py thêm pairing khi allowlist trống, secret sai và retry. Chạy toàn bộ **37 test methods, 0 failed, 0 errors** trên cùng DB test riêng; log `/tmp/room_rental_test_telegram_setup_final.log`. Bot API trong tests được mock; không gọi bot thật hoặc thay webhook thật. View Settings upgrade thành công; chưa kiểm tra trực quan bằng browser hoặc kết nối bot/tunnel thật với UI mới.

Sau bố trí lại UI Settings: upgrade view và 37 tests pass (`/tmp/room_rental_test_telegram_ui.log`); thông báo kết nối/ghép nối tiếp tục được rút gọn sau lần chạy này, pycodestyle pass. Browser automation không khởi tạo được (Windows sandbox helper lỗi), nên chưa xác nhận trực quan layout hoặc client next action trên browser.

Khối thông tin mã ghép nối dùng `role="status"` với class alert-info. Đã upgrade lại trên DB test, không còn warning accessibility về alert role; log `/tmp/room_rental_telegram_view_role.log`.

**Kết quả thực chạy 2026-10-06:** runtime `/home/lamnv/code/odoo-19/odoo-bin`, Python `/home/lamnv/.pyenv/versions/odoo19-env/bin/python`, PostgreSQL local; database riêng `room_rental_test_20261006`, HTTP test port 1379, không dùng config/local.conf hoặc bot thật. Cài addon và upgrade thành công; lần chạy cuối **25 test methods, 0 failed, 0 errors**, bao gồm test migration sửa stored totals/status cũ, render QWeb HTML và HTTP webhook. Log `/tmp/room_rental_test_20261006_final.log` nằm ngoài Git. Chưa kiểm thử PDF wkhtmltopdf, browser assets, race/stress đồng thời, bot/tunnel thật hoặc upgrade database dữ liệu production. Database test được giữ lại để chạy lại.

Mẫu test runner dùng DB riêng (thay các placeholder bằng runtime/addons-path thực tế; không dùng config DB/bot thật):

Sau format ngày 2026-10-06: kiểm tra toàn bộ 20 file Python custom (gồm tests/migration), không dòng code nào vượt 79 ký tự, comment/docstring không vượt 72; pycodestyle với max-line-length=79 pass. So sánh AST trước/sau không đổi logic hoặc chuỗi phản hồi (chỉ chuẩn hóa khoảng trắng trong docstring/description). Chạy lại 25 tests Odoo: 0 failed, 0 errors; log `/tmp/room_rental_test_20261006_format.log`. Không format dependency OCA.

```bash
<odoo_python> <odoo_source>/odoo-bin --config=/dev/null -d <test_db> \
  --addons-path=<odoo_source>/addons,project,addons_oca/addons_oca/web \
  --db_user=<test_db_user> --http-port=<test_port> --max-cron-threads=0 \
  -i room_rental_expense --test-enable --without-demo=all \
  --test-tags=/room_rental_expense --stop-after-init
```

Ưu tiên test có ý nghĩa: previous reading theo ngày, counter replacement/manual, giá trước/sau ngày hiệu lực, draft lock/link uniqueness, exact status transitions/pay reset, duplicate Telegram pay, secret/allowlist, ORM và XML/report upgrade compatibility.

Smoke flow: tạo phòng có default_rent + config → reading hai kỳ → tạo invoice UI (draft) → confirm → trả một phần/đủ → in PDF → cron chạy thủ công/instance có scheduler → Telegram reading/inv/show/lists/payment trên bot test. Test invalid date, counter regression, reading đã gắn invoice, room key trùng chéo. Không gọi bot thật hoặc dùng DB thật chỉ để chạy test.

## 14. Quy tắc làm việc và prompt dùng lại

`AGENTS.md` tại root là nguồn quy tắc chính:

- Trước task đọc code hiện tại, các phần context liên quan, config/flow/message liên quan.
- Docs thiếu/lệch phải đồng bộ trước hoặc trong task.
- Thay behavior thì cập nhật các phần tương ứng trong `AI_PROJECT_CONTEXT.md` trước khi kết thúc.
- Đổi lệnh/action/settings/integration/response format thì tài liệu phải phản ánh đúng behavior mới.

`project/room_rental_expense/AGENTS.md` bổ sung chỉ dẫn đặt code, giữ interface/import/manifest, đọc các điểm liên kết và kiểm chứng Odoo. Quy tắc chỉ nằm trong các AGENTS; mô tả kiến trúc/behavior vẫn nằm trong file context này. Khi đổi trách nhiệm hoặc đường dẫn source, cập nhật cả bảng **Đọc theo task** và bản đồ sửa code ở phần 13.

File context này là tài liệu tổng hợp duy nhất của project; không thay thế source. Không tạo lại cây tài liệu theo phase/module. Sau thay behavior, đồng bộ phần tương ứng ở file này để lần AI đọc sau không dùng snapshot lỗi thời. Không chép secrets từ local.conf/system parameters/log vào context.

Phân biệt mô tả hiện có và đề xuất: mục tiêu/checklist/hạng mục tương lai chưa phải behavior đã triển khai; kiểm tra source trước khi nói một tính năng đã tồn tại. Hướng dẫn AI chỉ dùng các AGENTS và context này; bộ workflow/metadata AI DevKit cũ đã được bỏ để tránh thêm lớp hướng dẫn trùng lặp. Cache Python là file sinh tự động, không thuộc source cần lưu. Report đang dùng nằm trong `reports/`; thư mục `report/` rỗng không cần giữ.

Prompt ngắn khi đưa file này cho AI:

```text
Hãy đọc AI_PROJECT_CONTEXT.md để hiểu project lamnv_utils và addon Odoo 19
room_rental_expense. Tài liệu mô tả snapshot source, các behavior và giới hạn
hiện có. Trước khi sửa, đọc AGENTS.md ở gốc, AGENTS.md của module,
bảng Đọc theo task, source và các phần context liên quan; ưu tiên
source khi có khác biệt. Không giả định các mục checklist đã được triển khai
hoặc test đã pass. Khi thay behavior, đồng bộ context này.

Task cần làm: <mô tả yêu cầu cụ thể>
```
