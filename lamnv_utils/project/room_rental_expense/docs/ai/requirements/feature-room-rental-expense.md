---
phase: requirements
title: Requirements & Problem Understanding
description: Retrospective requirements summary for the Odoo room rental expense module
feature: room-rental-expense
---

# Requirements & Problem Understanding

## Problem Statement
**What problem are we solving?**

- **Core Problem**: A renter needs one place in Odoo to track a room, monthly utilities, invoices, deposits, incidental expenses, and room issues instead of managing them across spreadsheets and chat history.
- **Who is affected?**: Individual renters or small operators who want lightweight room-cost tracking without a full ERP property stack.
- **Current situation/workaround**:
  - Utility readings are easy to lose or record inconsistently
  - Invoice totals depend on changing utility prices over time
  - Deposit, repair, and issue history is usually fragmented
  - Manual reminders for due invoices are unreliable

## Goals & Objectives
**What do we want to achieve?**

### Primary Goals
- Manage room master data and landlord information in one model
- Capture monthly electricity and water readings with support for meter replacement
- Generate invoices with automatic price application based on effective-date configuration, including cases with multiple invoices in the same month
- Preserve a real `draft -> pending -> partially_paid/paid/overdue/canceled` workflow where confirmed invoices are no longer freely editable
- Track payment state directly on invoices
- Record additional expenses, deposits, issue reports, and room history

### Secondary Goals
- Keep a historical snapshot of the configuration used for each invoice
- Provide printable invoice output
- Provide lightweight reporting views for invoices and expenses
- Add reminder automation for upcoming and overdue invoices
- Reduce duplicate data entry by generating invoice drafts directly from meter readings

### Non-Goals / Removed Scope
- Separate `room.payment` transaction model is not part of the final implementation
- Multi-room tenancy management, contracts, and full accounting integration are out of scope
- Advanced reconciliation and landlord payout workflows are out of scope

## User Stories & Use Cases
**How will users interact with the solution?**

- **As a renter**, I want to maintain the room and landlord profile, so that room-specific billing is anchored to one record.
- **As a renter**, I want to enter utility readings each month, so that electricity and water charges are calculated consistently.
- **As a renter**, I want invoices to pick the correct utility prices for a given period, so that price changes are preserved historically.
- **As a renter**, I want invoices to move through `draft`, `pending`, `partially_paid`, `paid`, `overdue`, and `canceled`, so that I can see the payment state at a glance.
- **As a renter**, I want to log deposits, incidental expenses, and room issues, so that I have a complete history of room-related costs and events.

### Key Flows Implemented
- Create a `rental.room`
- Maintain dated `room.config` records for utility pricing
- Enter a `meter.reading` and auto-fill previous counters
- Generate or open a monthly draft `room.invoice` directly from `meter.reading`
- Create a `room.invoice` and auto-apply room pricing plus meter usage
- Print invoice PDF and let cron update reminders and overdue state

### Edge Cases Covered
- Meter replacement for electricity and water
- Manual override of calculated utility usage
- Prevent deleting meter readings already linked to invoices
- Prevent linking meter readings and invoices across different rooms
- Prevent linking meter readings to invoices of a different month
- Prevent linking one meter reading to multiple invoices and keep meter/invoice room-month consistency
- Fallback to `ir.config_parameter` defaults when no room-specific config exists

## Success Criteria
**How will we know when we're done?**

### Delivered Outcomes
- `rental.room`, `meter.reading`, `room.invoice`, `room.expense`, `room.config`, `room.history`, `room.deposit`, and `room.issue` models exist
- Main menu plus reporting entries exist in the backend UI
- Invoice sequence, default config parameters, and daily cron job are installed
- Invoices can be printed through a QWeb PDF report
- Current code preserves the applied config on each invoice and enforces meter/invoice integrity rules

### Acceptance Criteria Reflected in Current Code
1. `room.config` is resolved by `effective_date <= invoice reference date`
2. Invoice amounts are computed from rent, usage, utility fees, other charges, and discount
3. Meter readings auto-suggest prior counters from the same room
4. Draft invoices stay editable until explicitly confirmed
5. Once an invoice leaves `draft`, core pricing and linkage fields are locked
6. Meter readings can generate a linked invoice directly, while preserving one reading per invoice linkage
7. Expense and invoice reporting menus are available through pivot/graph/list views

## Constraints & Assumptions
**What limitations do we need to work within?**

### Technical Constraints
- Target platform is Odoo 19 (`version: 19.0.1.0.0`)
- Dependencies are limited to `base`, `web`, and `mail`
- Payment tracking is invoice-field based, not ledger based
- Access rights are broad and only scoped to `base.group_user`

### Assumptions
- One invoice usually maps to one room and optionally one meter reading
- Utility prices can change over time and must remain historically traceable
- Room usage is personal or low-scale, so simple full-access permissions are acceptable

## Questions & Open Items
**What do we still need to clarify?**

- Should invoice payment tracking remain field-based, or should a dedicated payment model be reintroduced later?
- Should deleted automated tests be restored before further expansion?
- Should reminder activities target a specific user or be configurable per room?
