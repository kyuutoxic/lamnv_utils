# lamnv_utils — ngữ cảnh project dành cho AI

> Đối chiếu source ngày **2026-10-06**. Đọc phần 1 trước để nắm nhanh; các phần sau giải thích chi tiết và chỉ đến nơi cần sửa. File này có thể đưa riêng cho AI, không cần đính kèm các README khác để hiểu kiến trúc và nghiệp vụ chính.
>
> Đây là mô tả code đang có, không phải cam kết mọi flow đã chạy thành công. Chưa chạy Odoo/database trong lần tổng hợp này. Khi sửa code, kiểm tra lại file nguồn vì tài liệu là snapshot. Không chứa mật khẩu, bot token hay webhook secret thật.

## Đọc theo task

Đọc `AGENTS.md` ở gốc và phần 1 trước. Khi sửa addon, đọc thêm `project/room_rental_expense/AGENTS.md`. Sau đó dùng bảng này để đọc có chọn lọc; không cần nạp toàn bộ source OCA cho mỗi task.

| Task | Phần context cần đọc | Source cần mở trước |
| --- | --- | --- |
| Onboarding / hỏi tổng quan | 1–4, 12 | Manifest, models/__init__.py; mở model cụ thể khi cần xác minh |
| Phòng, chủ phòng, tổng tài chính, lịch sử | 4, 6, 12 | models/rental_room.py, models/room_history.py, views/rental_room_views.xml |
| Chỉ số điện/nước, thay công tơ, khóa reading | 5, phần liên kết ở 6, 12, 13 | models/meter_reading.py, models/room_invoice.py, views/meter_reading_views.xml |
| Giá, thành phần tiền, hóa đơn | 4, 6, 8, 10, 12, 13 | models/room_config.py, models/room_invoice.py, models/rental_room.py, invoice view/report |
| Thanh toán, state, reminder | Bảng trạng thái ở 6, 7 nếu có Telegram, 9–10, 12–13 | room_invoice actions/_auto_update_status/cron, meter_reading payment handlers, cron_data.xml |
| Telegram, lệnh, response, settings | 5–7, 10, 12–13 | controllers/telegram_webhook.py, models/meter_reading.py, models/res_config_settings.py |
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

`lamnv_utils` là workspace custom addon cho **Odoo 19**, hiện có một addon nghiệp vụ tự viết: **`project/room_rental_expense`**, version manifest `19.0.1.0.0`, author `lamnv`, license `LGPL-3`, application bật, auto-install tắt.

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
- `models/meter_reading.py` chứa cả nghiệp vụ công tơ và toàn bộ parser/dispatcher/handler Telegram.
- Mức tiêu thụ thường = số hiện tại − số cũ. Thay công tơ và nhập tay được hỗ trợ trong Odoo backend.
- Chỉ số trước là **bản ghi gần nhất có ngày nhỏ hơn ngày đang xét**, không bắt buộc tháng liền trước.
- Tạo hóa đơn từ UI chỉ số để lại nháp; `/inv` tạo mới sẽ tự xác nhận nếu tổng tiền > 0.
- Đã có hóa đơn thì khóa các trường lõi của reading và chặn xóa reading. Hóa đơn rời `draft` thì khóa các trường lõi; tiền đã trả và ghi chú vẫn sửa được.
- Chỉ một hóa đơn được liên kết với một reading qua constraint khai báo `unique(meter_reading_id)`. Chưa có unique phòng/ngày hoặc phòng/tháng cho reading/hóa đơn.
- Telegram chỉ xử lý slash command. Phòng được tìm bằng **OR** trên `telegram_code`, `room_number`, `name`; không phải tìm theo thứ tự ưu tiên.
- Secret và chat allowlist chỉ được kiểm tra nếu đã cấu hình; webhook sử dụng `sudo()`.
- Local config đặt port `1369`, database `room_rental_dev`, `workers=0`, **`max_cron_threads=0`**. Có cron trong addon không đồng nghĩa cron chạy trên local này.
- Chưa có test tự động cho addon nghiệp vụ. Test trong OCA không chứng minh flow phòng trọ đã được kiểm thử.

## 2. Cấu trúc và ranh giới repository

```text
lamnv_utils/
├── AGENTS.md                         quy tắc chung và thứ tự đọc theo task
├── AI_PROJECT_CONTEXT.md             file onboarding độc lập này
├── config/local.conf                cấu hình instance local; có dữ liệu bí mật
├── project/room_rental_expense/
│   ├── AGENTS.md                     chỉ dẫn riêng của addon Odoo
│   ├── __manifest__.py, __init__.py
│   ├── models/                       8 model nghiệp vụ + settings extension
│   ├── controllers/telegram_webhook.py
│   ├── security/ir.model.access.csv
│   ├── data/                         sequence, mặc định, cron
│   ├── views/                        10 XML view/menu/settings
│   ├── reports/invoice_template.xml
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

Addon root import `models`, `controllers`. `models/__init__.py` import phòng, công tơ, hóa đơn, chi phí, giá, lịch sử, cọc, sự cố, settings. Controller được import qua `controllers/__init__.py`.

Thứ tự load dữ liệu: ACL → sequence → system parameters → cron → report → các views → menu. Asset custom duy nhất được manifest đưa vào `web.assets_backend` là `currency_widget.js`. Không có frontend SPA/build npm riêng cho nghiệp vụ.

Odoo ORM quản lý PostgreSQL; binary ảnh có `attachment=True` dùng cơ chế attachment/filestore Odoo. Telegram outbound dùng `urllib` tiêu chuẩn; cron dùng `dateutil.relativedelta`.

## 4. Mô hình dữ liệu

Tất cả đường dẫn model trong bảng thuộc `project/room_rental_expense/models/`.

| Model / file | Dữ liệu và trách nhiệm |
| --- | --- |
| `rental.room` / `rental_room.py` | Phòng, địa chỉ, tòa nhà, diện tích, loại phòng, thời gian thuê, ảnh, chủ phòng, ngân hàng, `telegram_code`, `default_rent`, tổng tài chính |
| `room.config` / `room_config.py` | Giá điện, nước, wifi, rác, xe, tiện ích khác theo phòng và ngày hiệu lực |
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

Không lọc trạng thái; nháp và hóa đơn hủy vẫn được cộng. `room.history.total_spent` là non-stored compute: tổng toàn bộ hóa đơn + chi phí của phòng liên kết, không giới hạn `from_date/to_date`, không cộng cọc. `avg_rent` nhập tay, không tự tính.

### Selection và validation

- Loại phòng: `single`, `double`, `studio`, `shared` (default `single`). Phòng chỉ kiểm tra bắt đầu không sau kết thúc; bằng nhau được chấp nhận. Khai báo unique `telegram_code` bằng `_sql_constraints`.
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

`meter_reading_id` optional, `ondelete='set null'`; `meter.reading.invoice_id` cũng set null khi xóa invoice. Invoice khai báo unique meter_reading_id và constraint cùng phòng/cùng tháng, reading không được thuộc invoice khác.

`_sync_meter_readings()` tìm reading đang trỏ invoice, tháo liên kết cũ, gắn reading được chọn, chép electric/water usage. Chỉ gọi khi create hoặc write có `meter_reading_id`; onchange cũng chép usage cho form. Không có constraint unique invoice_month theo phòng.

### Trạng thái: đọc đúng thứ tự điều kiện

`_auto_update_status(force_pending=False)` xét từng invoice theo đúng thứ tự:

| Thứ tự | Điều kiện | Kết quả |
| --- | --- | --- |
| 1 | status hiện tại `canceled` | Bỏ qua, giữ canceled |
| 2 | total <= 0 và chưa trả | draft |
| 3 | remaining <= 0 và total khác 0 | paid |
| 4 | paid > 0 và remaining > 0 | partially_paid |
| 5 | due_date < hôm nay và trạng thái đang pending/partial/overdue | overdue |
| 6 | force_pending và trạng thái đang draft | pending |
| 7 | Không khớp | Giữ nguyên trạng thái |

Hệ quả: partial payment có ưu tiên cao hơn overdue; draft chưa trả không tự thành overdue chỉ vì hết hạn; force_pending chỉ đổi draft. Không giả định đây là state machine đầy đủ hoặc luôn tự phục hồi paid/overdue.

Actions: `action_confirm()` chỉ xử lý draft, yêu cầu total > 0 rồi đặt pending; `action_paid()` đặt paid_amount = total; `action_cancel()` đặt canceled. UI ẩn nút theo status nhưng Python actions không có mọi guard tương ứng.

`write()` kiểm tra set `_locked_after_draft_fields` trước khi ghi. Set gồm phòng, tháng, ngày, hạn, reading, rent, điện/nước usage và giá, utilities, phí khác, discount. Đổi status cùng lúc không bỏ qua kiểm tra trạng thái cũ. Paid_amount, notes, status không thuộc set khóa. Không có override invoice unlink để cấm xóa theo trạng thái.

Validation ngày: due_date không trước invoice_date (bằng nhau được phép). Tháng parse bằng datetime. Validation không âm kiểm tra rent, giá/usage điện/nước, utilities, discount, paid_amount; **other_charges có trong decorator nhưng bị thiếu trong tuple kiểm tra**. Không có kiểm tra discount <= subtotal hoặc paid_amount <= total ở ORM chung.

## 7. Telegram: giao thức và flow

### Inbound controller

`controllers/telegram_webhook.py` khai báo POST `/room_rental_expense/telegram/webhook`, `type='http'`, `auth='public'`, `csrf=False`.

1. Đọc JSON bằng `get_json(silent=True) or {}`; dùng parameter sudo.
2. Lấy secret từ header `X-Telegram-Bot-Api-Secret-Token`, fallback `kwargs.get('secret')` (query/form parameter của route). Không đọc `payload['secret']` từ JSON để xác thực.
3. Chỉ khi configured secret khác rỗng và không khớp thì trả HTTP 403: `{"ok":false,"error":"invalid_secret"}`.
4. Nhận `message` hoặc `edited_message`. Không có message thì HTTP 200: `{"ok":true,"ignored":true}`.
5. Gọi `env['meter.reading'].sudo().process_telegram_message(message)`.
6. Gửi message kết quả qua Bot API `sendMessage`, rồi trả result JSON HTTP 200.

Outbound sendMessage POST JSON gồm `chat_id`, `text`, timeout 10 giây. Thiếu token/chat/text thì bỏ qua gửi. `URLError` được log và không cố ý rollback nghiệp vụ. Không có retry/queue, không kiểm tra body `ok` của sendMessage, không chia tin dài.

### Command và cú pháp

| Lệnh | Hành vi |
| --- | --- |
| `/help` | Trả danh sách lệnh |
| `/reading P101 350 28 [YYYY-MM-DD]` | Ghi/cập nhật chỉ số điện, nước; không có ngày thì hôm nay |
| `/reading room:P101 elec:350 water:28 [date:YYYY-MM-DD]` | Cùng nghiệp vụ theo format key:value, giữ thứ tự này |
| `/inv P101 YYYY-MM-DD` | Tìm reading đúng ngày; lấy invoice đã có hoặc tạo mới rồi confirm nếu total > 0 |
| `/show INV-2026-0001` | Chi tiết invoice và manual_breakdown |
| `/invoices P101` | Tối đa 10 invoice, sort kỳ/ngày/id giảm dần, gồm cả canceled |
| `/readings P101` | Tối đa 10 reading, sort ngày/id giảm dần |
| `/paid INV-2026-0001` | Ghi đã trả đủ bằng action_paid |
| `/pay INV-2026-0001 1000000` | Cộng số tiền > 0, cap ở total_amount, gọi cập nhật status force_pending |
| `/unpaid INV-2026-0001` | Reset paid_amount = 0 rồi cập nhật status force_pending |

Dispatcher so sánh uppercase nên tên lệnh không phân biệt hoa thường; mã phòng và số invoice search `=` giữ nguyên chuỗi. Chưa hỗ trợ `/start`, `/help@botname`, `/reading@botname ...`, callback query, ảnh/OCR, thay công tơ/manual override qua syntax command.

Parser reading dùng fullmatch, số không âm, chấp nhận dấu `.` hoặc `,` làm thập phân; room key một token không chứa khoảng trắng. `_parse_telegram_amount()` xóa mọi dấu `.` và `,` rồi float: `1.000.000` → 1000000; `1,5` → 15, không phải 1.5.

### Tìm phòng và upsert

Room lookup là domain OR trên ba field, limit 2: không có → lỗi; >1 → lỗi “mã phòng bị trùng”, kể cả một record khớp telegram_code và record khác khớp room_number/name. `telegram_code` duy nhất vẫn không loại trừ sự trùng chéo này. Khi xây ví dụ command trả về, bot ưu tiên reference telegram_code → room_number không chứa space → name không chứa space.

Upsert đọc `(room_id,reading_date)` chính xác, lấy record mới nhất khi có nhiều bản ghi trùng. Luôn chuẩn bị số trước, preview bằng `new(vals)` rồi kiểm tra regression. Existing có invoice thì lỗi; chưa có invoice thì write; không tìm thấy thì create. Không có SQL unique cho key upsert, không có khóa chống race.

`process_telegram_message()` lấy text, kiểm tra allowlist chat ID, dispatch và bắt **ValidationError** để trả `status:error`. Allowlist CSV được so sánh `str(chat.id)`, không kiểm tra quyền `from.id` hay ownership phòng. Rỗng allowlist cho phép mọi chat. Không dùng savepoint rõ ràng bao quanh handler; exception loại khác có thể thành lỗi HTTP ngoài schema result thông thường.

### Kết quả và idempotency

Success dùng `status:'success'`, `message`, tùy command có `reading_id`, `invoice_id`, `action:'created'/'updated'`. Validation error dùng `status:'error'`, `message`; cả hai thường HTTP 200. Không suy luận tất cả response có `ok:true`.

Tin reading thành công có phòng, reference, ngày/tháng, số cũ → mới và usage, gợi ý `/inv`. Invoice summary có status key tiếng Anh, tiền phòng/điện/nước/tiện ích/phí/giảm/tổng/đã trả/còn lại, khối “Chi tiết”, gợi ý paid/pay. Payment summary có status/đã trả/còn lại. Tiền format dấu chấm nghìn, 0 chữ số thập phân.

Không lưu/deduplicate `update_id` hoặc message ID. Telegram retry/edited_message của `/pay` có thể cộng tiền lại. `/inv` dùng invoice đã gắn để tránh tạo lại trên cùng reading. `/unpaid` không bảo đảm luôn chuyển paid về pending vì bảng trạng thái giữ paid nếu không khớp điều kiện đổi; canceled cũng luôn được giữ.

### Settings và setup

Ba config_parameter field: telegram_bot_token, telegram_webhook_secret, telegram_allowed_chat_ids. UI riêng trong Settings giới hạn `base.group_system`, token/secret hiển thị password.

`action_register_telegram_commands()` lấy token từ field hiện tại hoặc parameter đã lưu, POST `setMyCommands` với chín lệnh trong bảng, timeout 15 giây; thiếu token/URLError/API ok false → UserError; thành công → display_notification. Nút này **không setWebhook**, không lấy chat ID và không tự lưu toàn bộ field settings trước khi gọi API.

Setup vận hành: tạo bot bằng BotFather → cấu hình token/secret/chat IDs → chuẩn bị telegram_code cho phòng → public HTTPS/tunnel tới đúng port instance → gọi setWebhook với URL và secret_token → kiểm tra getWebhookInfo → đăng ký suggestions → test `/help`, reading, inv, show.

#### Thiết lập Telegram từng bước

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

Phòng mở `kanban,list,form`; kanban có tài chính, ảnh, chủ phòng, count, thời gian thuê. Badge “Sắp hết hạn” chỉ kiểm tra có end_date, không tính khoảng cách đến ngày hết hạn. Form có notebook các quan hệ và chatter. Nút xem hóa đơn/chỉ số từ phòng trả `view_mode='tree,form'` trong Python, trong khi XML chính dùng `list,form`; đây là điểm cần smoke test Odoo 19.

Reading form có tổng quan, tab điện/nước, cờ thay, nhập tay, ảnh, tạo/mở hóa đơn. Readonly XML không hoàn toàn giống set khóa Python (ví dụ replacement_last), nên guard server vẫn là nguồn quyết định cuối.

Invoice form có confirm/paid/cancel/PDF, statusbar, chi tiết và ghi chú, paid_amount vẫn editable. Action invoice chính lọc `status != canceled`; không có nghĩa dữ liệu hủy biến mất khỏi totals/report/Telegram. Search invoice có nhóm phòng/tháng/status, lọc hạn/overdue/nháp/đã trả; search reading nhóm phòng/tháng, lọc thay; expense nhóm phòng/category. Không khai báo riêng pivot/graph view trong addon, report action sử dụng view mặc định Odoo.

`currency_widget.js` đăng ký:

- `vnd_currency`: subclass FloatField; Math.round, dấu chấm phân nghìn, hậu tố ` ₫`.
- `number_format`: subclass FloatField; integer phân nghìn, decimal tối đa 2 chữ số rồi trim; cách dùng cùng dấu chấm có thể gây mơ hồ giữa nghìn/thập phân.
- `window.formatVND` helper global. Format chỉ hiển thị; không đổi kiểu trường hoặc quy tắc tính tiền.
- Kanban dùng các field Python `*_fmt`, không gọi widget để format trực tiếp.

`reports/invoice_template.xml`: QWeb `report_room_invoice` gọi `web.external_layout`, loop docs, hiển thị phòng, kỳ, ngày/hạn, bảng tiền, đã trả/còn lại, manual_breakdown, notes. Action `report_room_invoice_pdf`, type qweb-pdf; tên file `Invoice - <invoice_number>`. Template dùng t-esc giá trị tiền trực tiếp, không dùng widget VND. `action_print_invoice()` trả False nếu không tìm được XML ID report. Chưa kiểm chứng report tag/layout với runtime Odoo 19 trong lần này.

## 9. Cron và reminder

`data/cron_data.xml` tạo `cron_room_invoice_status_update`, name “Room Invoice Status Update”, interval 1 ngày, active, gọi `model.cron_update_overdue_status()`.

Method đọc reminder_days, parse int (ValueError fallback 3). Tìm invoice không paid/canceled, có due_date < today rồi gọi bảng auto status; vì ưu tiên partial/draft nên không phải tất cả kết quả search chuyển overdue.

Tìm invoice draft/pending/partial với due_date từ hôm nay đến hôm nay + reminder_days, tạo todo activity nếu chưa có cùng activity type và summary “Nhắc thanh toán hóa đơn”. Deadline = due_date, note gồm số/hạn/còn lại. Không có logic gửi Telegram nhắc hạn, email template riêng, hoặc tự close reminder khi đã thanh toán trong code custom này.

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
| `telegram_webhook_secret` | rỗng | Xác thực inbound nếu đã đặt |
| `telegram_allowed_chat_ids` | rỗng | CSV chat.id; rỗng bỏ kiểm tra |

Giá fallback float parse lỗi → 0. `noupdate=1` cũng áp dụng sequence và cron: upgrade module thường giữ dữ liệu đã cấu hình thay vì ghi lại XML defaults. Giá thực tế lấy từ DB, không mặc định luôn bằng bảng này.

### Local instance

`config/local.conf`: PostgreSQL localhost:5432, user lamnv, db room_rental_dev; bind XML-RPC 0.0.0.0, configured port 1369; workers 0, max_cron_threads 0, limit_time_real 12000, log_level info, proxy_mode False, server_environment dev. Có khóa `admin_passwd`, `db_password`, `secret_key`; không copy giá trị vào prompt/file context.

addons_path gồm `project`, hai đường dẫn core Odoo bên ngoài, `addons_oca/addons_oca/web`, `~/code/learn_odoo`. Config có thể chứa option kế thừa/custom; phải xác minh Odoo runtime đọc option nào, không khẳng định bind/port chỉ dựa file này.

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
2. **Quyền rộng:** ACL cho cả 8 model CRUD đầy đủ với base.group_user; không có record rules custom. Webhook sudo và secret/allowlist optional; production phải chủ động cấu hình kiểm soát truy cập.
3. **Tổng phòng không lọc hủy/nháp**, history không lọc thời gian; cọc/chi phí không tự vào invoice.
4. **Reading không unique phòng/ngày/tháng**; invoice không unique số/tháng/phòng; `_sql_constraints` là khai báo cần kiểm tra thực sự cài vào DB Odoo 19.
5. **Đồng bộ liên kết không đối xứng hoàn toàn:** invoice điều khiển sync; ghi trực tiếp reading.invoice_id không chạy chiều ngược. Không tự cascade recalculation kỳ sau khi sửa reading trước.
6. **Bảng status có điều kiện giữ trạng thái cũ:** partial quá hạn vẫn partial; draft hết hạn chưa tự overdue; unpaid trên paid có thể vẫn paid. Hóa đơn canceled vẫn có thể bị đổi paid_amount bởi actions/commands nhưng auto status bỏ qua canceled.
7. **Validation tài chính chưa đầy đủ:** other_charges âm không bị tuple constraint chặn; discount vượt subtotal/overpayment không bị constraint chung chặn; các model bổ trợ không kiểm tra số âm/ngày.
8. **Create áp giá force** có thể ghi đè giá tay; rent 0 có thể bị thay bằng default_rent. Reprice theo invoice_date, không chỉ theo invoice_month.
9. **Telegram chưa dedup/retry-safe cho pay**, chưa normalize command @botname, chưa chia message dài, chưa xử lý file/OCR; chỉ ValidationError được chuyển schema lỗi nghiệp vụ.
10. **UI và runtime cần kiểm tra:** action Python còn tree,form; report dùng tag report; compatibility các API/constraint Odoo 19 chưa được xác nhận bằng khởi động trong lần tạo tài liệu. Kanban badge không thực sự kiểm tra sắp hết hạn.
11. **Local cron tắt**, public tunnel/outbound/token không thể xác nhận từ code. Không có Prometheus/Grafana/APM custom đã triển khai trong addon. Khi theo dõi vận hành, kiểm tra Odoo/proxy logs, webhook 403/5xx, reply failures, lần chạy cron và reminder activities; đây là hướng dẫn, không phải monitoring đã tích hợp.
12. **Test chưa có cho custom addon**; `.gitignore` module có pattern test_*.py, cần kiểm tra tracking khi thêm tests để không vô tình bỏ sót test file.

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

Chưa có bộ test custom để chạy ngay. Các gợi ý kiểm chứng bên dưới là checklist, không phải kết quả tests đã pass. Khi bổ sung tests đặt trong `project/room_rental_expense/tests/`, import tests đúng chuẩn Odoo và kiểm tra .gitignore.

Mẫu test runner sau khi đã thêm tests, dùng DB riêng:

```bash
python ../odoo/odoo-bin -c config/local.conf -d <test_db> \
  -i room_rental_expense --test-enable \
  --test-tags /room_rental_expense --stop-after-init
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
