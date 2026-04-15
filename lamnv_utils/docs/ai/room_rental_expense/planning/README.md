---
phase: planning
title: Project Planning & Task Breakdown
description: Break down work into actionable tasks and estimate timeline
---

# Project Planning & Task Breakdown

## Milestones

- [x] Milestone 1: Hoàn thiện phạm vi nghiệp vụ và mô hình dữ liệu cho module phòng trọ.
- [x] Milestone 2: Hoàn thiện các luồng cốt lõi: phòng, chỉ số, hóa đơn, cấu hình giá.
- [x] Milestone 3: Hoàn thiện các luồng bổ trợ: chi phí, cọc, sự cố, báo cáo, Telegram webhook.
- [ ] Milestone 4: Bổ sung test tự động và hardening triển khai thực tế.

## Task Breakdown

### Phase 1: Foundation

- [x] Tạo model `rental.room` làm trung tâm dữ liệu.
- [x] Tạo model `room.config` để quản lý giá theo hiệu lực.
- [x] Khai báo ACL và sequence hóa đơn.
- [x] Tạo menu và form/list view cơ bản.

### Phase 2: Core Features

- [x] Xây dựng model `meter.reading` với logic previous reading.
- [x] Xử lý thay công tơ và manual override cho usage.
- [x] Xây dựng model `room.invoice` với công thức tiền và vòng đời trạng thái.
- [x] Đồng bộ hóa đơn với chỉ số công tơ.
- [x] Tạo report PDF hóa đơn.

### Phase 3: Integration & Polish

- [x] Tạo model `room.expense`, `room.deposit`, `room.issue`, `room.history`.
- [x] Tạo cron cập nhật overdue và reminder activity.
- [x] Tích hợp Telegram webhook và command handlers.
- [x] Tạo giao diện cấu hình backend cho Telegram/system parameters.
- [x] Tạo action đăng ký Telegram command suggestions từ Settings.
- [x] Thêm widget JS format VND/number cho backend UI.
- [ ] Viết test tự động.

## Dependencies

- Odoo 19 runtime và các module `base`, `web`, `mail`.
- Telegram Bot token và webhook secret nếu bật tích hợp Telegram.
- Cần có route public truy cập được từ Telegram khi chạy production.

## Timeline & Estimates

Ước lượng nếu tiếp tục hoàn thiện module:

- Test tự động cho model và webhook logic: `1-2 ngày`
- Hardening Telegram flow, smoke test và tinh chỉnh tài liệu: `0.5-1 ngày`
- Smoke test + fix edge cases: `0.5-1 ngày`

## Risks & Mitigation

- Rủi ro sai công thức khi thay công tơ:
  - Mitigation: test riêng cho các case meter replacement và manual override.
- Rủi ro route public Telegram bị lạm dụng:
  - Mitigation: bật secret token, chat allowlist, logging cảnh báo.
- Rủi ro dữ liệu inconsistent giữa chỉ số và hóa đơn:
  - Mitigation: giữ unique meter-to-invoice, khóa sửa/xóa sau khi liên kết.
- Rủi ro mở rộng dữ liệu làm chậm list/filter:
  - Mitigation: bổ sung test hiệu năng và cân nhắc SQL constraint/index cho reading.

## Resources Needed

- 1 Odoo developer để bổ sung test và hardening.
- 1 môi trường Odoo dev/staging có cấu hình webhook public.
- 1 Telegram bot dùng riêng cho module.
