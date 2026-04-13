---
phase: planning
title: Project Planning & Task Breakdown
description: Retrospective milestone view for the Odoo room rental expense module
feature: room-rental-expense
---

# Project Planning & Task Breakdown

## Milestones
**What are the major checkpoints?**

- [x] Milestone 1: Create initial Odoo 19 room rental management module scaffold
- [x] Milestone 2: Expand billing logic with config snapshots, reminders, and PDF invoice output
- [x] Milestone 3: Clean up repository artifacts and improve UI presentation

## Task Breakdown
**What specific work has been done?**

### Phase 1: Foundation
- [x] Implement room, meter, invoice, expense, config, history, deposit, and issue models
- [x] Create security access file for all active models
- [x] Build list/form/search views and menu structure for the main workflow

### Phase 2: Core Billing Features
- [x] Remove the unused `room.payment` path and consolidate payment state onto invoices
- [x] Add invoice numbering sequence
- [x] Add default configuration parameters for pricing fallbacks
- [x] Add invoice report template and print action
- [x] Add daily cron for overdue update and reminder scheduling
- [x] Expand meter replacement and manual-usage handling
- [x] Tighten invoice and meter integrity rules around room/month matching, edit locking, and one-reading-per-invoice linkage
- [x] Align invoice workflow so `draft` remains editable until explicit confirmation
- [x] Lock core invoice and meter fields after confirmation/linking
- [x] Validate invoice month format and room/month consistency with linked meter readings
- [x] Complete utility fallback pricing for wifi, trash, parking, and other default fees
- [x] Fix invoice PDF template to iterate properly over `docs`
- [x] Add meter-reading actions to generate or open the linked invoice draft

### Phase 3: Cleanup & UX
- [x] Remove `__pycache__` artifacts and obsolete files from version control
- [x] Add module-level `.gitignore`
- [x] Improve room and billing views
- [x] Add backend currency formatting widget
- [x] Remove temporary automated test files during cleanup
- [x] Remove obsolete markdown documents that drifted from the codebase
- [x] Add module-scoped `docs/ai` documentation inside `room_rental_expense`

## Dependencies
**What needs to happen in what order?**

- Room master data must exist before room-specific config, readings, or invoices
- Config and/or default parameters must exist before predictable invoice pricing
- Meter readings should exist before invoice generation if usage is to be imported automatically
- Cron effectiveness depends on due dates and mail activity support from `mail`

## Timeline & Estimates
**When did the work happen?**

- `2025-11-14`: initial module creation in commit `8e9a4cc`
- `2025-11-17`: major functional enhancement in commit `cd3eda1`
- `2025-11-19`: cleanup and UI pass in commit `8af3008`
- `2026-04-13`: post-review hardening of invoice workflow, meter/invoice linkage rules, support for multiple invoices/readings in the same month, and module-local AI documentation

## Risks & Mitigation
**What could go wrong?**

- **Risk**: invoice behavior regresses because tests were removed
  - **Mitigation**: reintroduce automated tests around invoice and meter flows first
- **Risk**: full CRUD access for all internal users is too broad
  - **Mitigation**: introduce groups and record rules if the module is shared beyond personal use
- **Risk**: payment-state-only design becomes insufficient
  - **Mitigation**: add a proper payment model only when reconciliation requirements appear

## Resources Needed
**What do we need next?**

- Odoo test coverage restoration
- Real sample data for manual regression checks
- Decision on whether the module stays personal-use or moves toward broader multi-user support
