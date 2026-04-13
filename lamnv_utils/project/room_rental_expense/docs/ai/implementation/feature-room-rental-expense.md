---
phase: implementation
title: Implementation Guide
description: What was implemented in the Odoo room rental expense module
feature: room-rental-expense
---

# Implementation Guide

## Development Setup
**How do we get started?**

### Prerequisites
- Odoo 19 environment
- Module path available under `lamnv_utils/project/room_rental_expense`
- Dependencies: `base`, `web`, `mail`

### Installed Data
- `security/ir.model.access.csv`
- `data/room_sequence.xml`
- `data/room_config_data.xml`
- `data/cron_data.xml`
- `reports/invoice_template.xml`
- All model views plus `views/menu_views.xml`

## Code Structure
**How is the code organized?**

### Current Models
```text
models/
├── rental_room.py
├── meter_reading.py
├── room_invoice.py
├── room_expense.py
├── room_config.py
├── room_history.py
├── room_deposit.py
└── room_issue.py
```

### Historical Evolution Across Commits
- `8e9a4cc`: initial Odoo 19 module scaffold with room, meter, invoice, payment, expense, config, history, deposit, and issue models
- `cd3eda1`: major functional expansion
  - removed `room.payment`
  - added `USAGE.md`
  - added sequence, default config parameters, daily cron, PDF report
  - expanded invoice and meter logic
  - added tests temporarily
- `8af3008`: cleanup and UX pass
  - removed caches and obsolete tests
  - added module `.gitignore`
  - improved room views and currency display widget

## Implementation Notes
**Key technical details to remember:**

### Core Features

#### Room Master Record
- `rental.room` stores room identity, landlord information, default rent, attachments, and chatter tracking
- Computed totals aggregate invoice and expense data back onto the room
- Smart actions open invoices and meter readings filtered to the current room

#### Effective-Dated Utility Configuration
- `room.config` stores per-room prices with `effective_date`
- `rental.room._get_active_config(reference_date)` resolves the latest valid config for a target date
- Invoices also store `applied_config_id` to preserve which config was used

#### Meter Reading Logic
- `meter.reading` computes `reading_month` and display name from the reading date
- Previous counters are auto-filled from the latest earlier reading of the same room
- Utility usage supports two modes:
  - automatic delta calculation
  - manual override through inverse-computed fields
- Meter replacement is supported by combining the old-meter delta with the new counter value
- Meter forms can generate a linked invoice directly, or reopen the linked invoice if it already exists
- Multiple readings and multiple invoices may coexist in the same month; continuity comes from the previous reading chain, not from monthly uniqueness

#### Invoice Lifecycle
- `room.invoice.create()` injects room defaults, assigns sequence, applies config prices, syncs selected meter readings, and updates status
- `room.invoice` enforces that one `meter.reading` can only be linked to one invoice at a time
- `write()` reapplies pricing when room/date changes and keeps meter links synchronized
- Computed monetary fields cover electric amount, water amount, subtotal, total amount, and remaining amount
- `manual_breakdown` generates a readable textual breakdown for the form and report
- When invoice creation starts from `meter.reading`, the room, month, date, and selected reading are prefilled automatically

#### Automation and Reminders
- `cron_update_overdue_status()` runs daily
- Overdue invoices are reclassified automatically
- Upcoming invoices within `room_rental_expense.reminder_days` schedule a mail activity reminder

### Patterns & Best Practices

#### Integrity Rules Implemented
- Meter reading room must match invoice room
- Due date cannot be before invoice date
- Meter readings linked to invoices cannot be deleted
- Counter rollback is rejected unless meter replacement is explicitly flagged

#### Fallback Pricing
- If no `room.config` exists for the invoice date, invoice pricing falls back to `ir.config_parameter`
- Default keys currently include electricity, water, wifi, trash, and reminder days

#### UI Behavior
- Room form tabs pass `default_room_id` through context
- Invoice and meter fields become effectively read-only in the workflow once business state advances
- Meter reading form exposes `Tạo Hóa Đơn` and `Mở Hóa Đơn` actions to drive the main billing workflow
- Report menus for invoice and expense analytics use `pivot,graph,list`

## Integration Points
**How do pieces connect?**

- `meter.reading` optionally links into `room.invoice` via `meter_reading_id` and back-reference `invoice_id`
- `room.invoice` consumes `room.config` and `ir.config_parameter`
- Cron calls invoice model logic directly
- Report action resolves `room_rental_expense.report_room_invoice_pdf`
- Frontend asset `static/src/js/currency_widget.js` is loaded through `web.assets_backend`

## Error Handling
**How do we handle failures?**

- Business rule violations use `ValidationError`
- Missing report definition fails safely and returns `False`
- Default pricing conversion guards against invalid parameter values

## Performance Considerations
**How do we keep it fast?**

- The module relies on standard Odoo ORM searches over room-scoped records
- `_get_active_config` searches only one room and returns one record ordered by latest effective date
- Roll-up totals are stored on `rental.room` for invoice and expense summaries

## Security Notes
**What security measures are in place?**

- All current business models grant full CRUD to `base.group_user`
- There are no record rules, company scoping rules, or specialized role splits yet
- Attachments are used for room images, receipts, issue photos, and meter photos
