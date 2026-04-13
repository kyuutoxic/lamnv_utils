---
phase: testing
title: Testing Strategy
description: Current testing status and recommended coverage for the Odoo room rental expense module
feature: room-rental-expense
---

# Testing Strategy

## Test Coverage Goals
**What level of testing do we aim for?**

- Validate invoice calculation logic, status transitions, config application, and meter-reading edge cases
- Cover critical Odoo ORM flows: `create`, `write`, computed fields, constraints, and cron behavior
- Preserve behavioral regressions introduced across pricing and room workflow changes

## Unit Tests
**What individual components need testing?**

### `meter.reading`
- [ ] Auto-calculate usage from previous and current counters
- [ ] Compute usage correctly when a meter is replaced
- [ ] Reject replacement-last values smaller than previous counter values
- [ ] Preserve manual override values through inverse logic
- [ ] Reject counter rollback when replacement is not flagged
- [ ] Reject deleting readings linked to an invoice
- [ ] Chain previous counters correctly when multiple readings exist in the same month
- [ ] Create a draft invoice directly from a reading when no invoice exists yet
- [ ] Reopen the linked invoice from a reading that already has one

### `room.invoice`
- [ ] Apply room default rent on create/onchange
- [ ] Default `invoice_date`, `invoice_month`, and `due_date` consistently on create
- [ ] Resolve correct `room.config` by effective date
- [ ] Fall back to all configured `ir.config_parameter` utility defaults when no config exists
- [ ] Compute `electric_amount`, `water_amount`, `subtotal`, `total_amount`, and `remaining_amount`
- [ ] Keep `draft` unchanged until explicit confirmation
- [ ] Update status correctly for pending, partially paid, paid, and overdue cases
- [ ] Reject edits to locked business fields after the invoice leaves `draft`
- [ ] Keep meter-reading linkage synchronized when `meter_reading_id` changes
- [ ] Reject linking the same meter reading to multiple invoices
- [ ] Reject meter readings whose month differs from the invoice month

### `rental.room`
- [ ] Aggregate `total_invoiced`, `total_paid`, `total_remaining`, and `total_expenses`
- [ ] Return the expected config from `_get_active_config`

## Integration Tests
**How do we test component interactions?**

- [ ] Room -> config -> invoice pricing flow across multiple effective dates
- [ ] Room -> meter reading -> invoice flow with automatic usage import
- [ ] Meter reading -> generate invoice action prefills room, month, date, and usage correctly
- [ ] Manual invoice creation cannot pick a meter reading already linked to another invoice
- [ ] Room -> invoice flow without room-specific config uses complete default utility bundle
- [ ] Cron run updates overdue invoices and schedules reminder activities
- [ ] Report action resolves successfully for a valid invoice

## End-to-End Tests
**What user flows need validation?**

- [ ] Create room, config, and first invoice with no previous readings
- [ ] Create later reading and invoice using prior counters
- [ ] Edit invoice dates and verify pricing snapshot changes to the expected config
- [ ] Mark partial payment and full payment, then verify final status
- [ ] Print invoice PDF and verify key totals and breakdown text

## Test Data
**What data do we use for testing?**

- One room with multiple dated configs
- Meter readings covering normal progression and replacement scenarios
- Invoice samples with and without meter linkage
- System parameters seeded for fallback pricing and reminder days

## Test Reporting & Coverage
**How do we verify and communicate test results?**

- Historical note: commit `cd3eda1` added `tests/test_calculations.py`
- Current state: the repository still lacks automated tests for this module
- Immediate priority is to restore automated coverage around invoice workflow locking, uniqueness constraints, report rendering, and meter integrity

## Manual Testing
**What requires human validation?**

- Form readonly behavior after invoice state changes
- Room tab context propagation when creating child records
- PDF layout readability
- Currency formatting widget behavior in backend views

## Performance Testing
**How do we validate performance?**

- Low priority for current scope
- Smoke-check creation and opening of rooms with larger invoice histories

## Bug Tracking
**How do we manage issues?**

- Focus defects by business area: pricing, meter integrity, reminders, reporting, and UI readonly rules
- Any future regression should reference the commit where the behavior was introduced or removed
