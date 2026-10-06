from datetime import timedelta
from pathlib import Path
import runpy

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestRoomInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.room = cls.env['rental.room'].create(
            {
                'name': 'Test room',
                'telegram_code': 'TEST101',
                'default_rent': 1000000,
            }
        )
        cls.config = cls.env['room.config'].create(
            {
                'room_id': cls.room.id,
                'effective_date': cls.today - timedelta(days=60),
                'electric_price': 4000,
                'water_price': 20000,
                'wifi_price': 100000,
            }
        )

    def invoice(self, **values):
        return self.env['room.invoice'].create(
            {
                'room_id': self.room.id,
                'invoice_date': self.today,
                'invoice_month': self.today.strftime('%m/%Y'),
                **values,
            }
        )

    def test_amounts_and_active_config(self):
        inv = self.invoice(
            electric_usage=10,
            water_usage=2,
            other_charges=50000,
            discount_amount=10000,
        )
        self.assertEqual(inv.applied_config_id, self.config)
        self.assertEqual(inv.electric_amount, 40000)
        self.assertEqual(inv.water_amount, 40000)
        self.assertEqual(inv.subtotal, 1230000)
        self.assertEqual(inv.total_amount, 1220000)
        self.assertEqual(inv.remaining_amount, 1220000)

    def test_config_effective_date(self):
        future = self.env['room.config'].create(
            {
                'room_id': self.room.id,
                'effective_date': self.today + timedelta(days=1),
                'electric_price': 5000,
                'water_price': 25000,
            }
        )
        self.assertEqual(self.invoice().applied_config_id, self.config)
        self.assertEqual(
            self.invoice(invoice_date=future.effective_date).applied_config_id,
            future,
        )

    def test_payment_status_reset(self):
        inv = self.invoice()
        inv.action_confirm()
        inv.paid_amount = 100000
        self.assertEqual(inv.status, 'partially_paid')
        inv.action_paid()
        self.assertEqual(inv.status, 'paid')
        inv.paid_amount = 0
        self.assertEqual(inv.status, 'pending')
        self.assertEqual(inv.remaining_amount, inv.total_amount)

    def test_overdue_partial_and_reset(self):
        inv = self.invoice(
            invoice_date=self.today - timedelta(days=2),
            due_date=self.today - timedelta(days=1),
        )
        inv.action_confirm()
        inv.paid_amount = 100000
        self.assertEqual(inv.status, 'overdue')
        inv.action_paid()
        self.assertEqual(inv.status, 'paid')
        inv.paid_amount = 0
        self.assertEqual(inv.status, 'overdue')

    def test_draft_not_automatically_overdue(self):
        inv = self.invoice(
            invoice_date=self.today - timedelta(days=2),
            due_date=self.today - timedelta(days=1),
        )
        inv._auto_update_status()
        self.assertEqual(inv.status, 'draft')

    def test_cancel_recomputes_room_totals(self):
        first, second = self.invoice(), self.invoice()
        first.paid_amount = 100000
        self.assertEqual(
            self.room.total_invoiced, first.total_amount + second.total_amount
        )
        first.action_cancel()
        self.assertEqual(self.room.total_invoiced, second.total_amount)
        self.assertEqual(self.room.total_paid, 0)
        self.assertEqual(self.room.total_remaining, second.remaining_amount)

    def test_financial_limits(self):
        inv = self.invoice()
        for values in (
            {'other_charges': -1},
            {'discount_amount': inv.subtotal + 1},
            {'paid_amount': inv.total_amount + 1},
            {'paid_amount': -1},
        ):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                inv.write(values)
        self.assertEqual(inv.paid_amount, 0)

    def test_canceled_cannot_be_paid(self):
        inv = self.invoice()
        inv.action_cancel()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            inv.action_paid()
        self.assertEqual(inv.status, 'canceled')
        self.assertEqual(inv.paid_amount, 0)

    @mute_logger('odoo.sql_db')
    def test_meter_link_and_lock(self):
        reading = self.env['meter.reading'].create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 100,
                'electric_current': 110,
                'water_previous': 10,
                'water_current': 12,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        self.assertEqual(reading.invoice_id, inv)
        self.assertEqual(inv.electric_usage, 10)
        self.assertEqual(inv.water_usage, 2)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.invoice(meter_reading_id=reading.id)
        inv.action_confirm()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            inv.rent_amount = 2000000

    @mute_logger('odoo.sql_db')
    def test_sql_constraints_installed(self):
        self.env.flush_all()
        for table, suffix in (
            ('rental_room', 'rental_room_telegram_code_unique'),
            ('room_config', 'room_config_unique_effective_date'),
            ('room_invoice', 'room_invoice_unique_meter_reading'),
        ):
            self.cr.execute(
                'SELECT 1 FROM pg_constraint WHERE conrelid = %s::regclass '
                'AND conname = %s',
                [table, f'{table}_{suffix}'],
            )
            self.assertTrue(self.cr.fetchone(), table)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['rental.room'].create(
                {'name': 'Duplicate', 'telegram_code': 'TEST101'}
            )
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.config.copy()

    def test_report_and_list_actions(self):
        inv = self.invoice()
        action = inv.with_context(
            discard_logo_check=True
        ).action_print_invoice()
        self.assertEqual(action['report_type'], 'qweb-pdf')
        report = self.env.ref('room_rental_expense.report_room_invoice_pdf')
        html, _ = report._render_qweb_html(report.report_name, inv.ids)
        self.assertIn(inv.invoice_number.encode(), html)
        self.assertEqual(
            self.room.action_view_invoices()['view_mode'], 'list,form'
        )
        self.assertEqual(
            self.room.action_view_meter_readings()['view_mode'], 'list,form'
        )

    def test_upgrade_refreshes_existing_totals_and_status(self):
        inv = self.invoice()
        inv.action_cancel()
        outstanding = self.invoice()
        self.env.flush_all()
        # Simulate stored values left by version 19.0.1.0.0.
        self.cr.execute(
            'UPDATE rental_room SET total_invoiced = %s, total_remaining = %s '
            'WHERE id = %s',
            [inv.total_amount * 2, inv.total_amount * 2, self.room.id],
        )
        self.cr.execute(
            "UPDATE room_invoice SET status = 'paid' WHERE id = %s",
            [outstanding.id],
        )
        self.env.invalidate_all()
        migration = (
            Path(__file__).resolve().parents[1]
            / 'migrations/19.0.1.1.0/post-migrate.py'
        )
        runpy.run_path(str(migration))['migrate'](self.cr, '19.0.1.0.0')
        self.assertEqual(self.room.total_invoiced, outstanding.total_amount)
        self.assertEqual(
            self.room.total_remaining, outstanding.remaining_amount
        )
        self.assertEqual(outstanding.status, 'pending')
