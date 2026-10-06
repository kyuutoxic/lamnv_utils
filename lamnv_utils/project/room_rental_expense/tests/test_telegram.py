import json

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTelegramPayments(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '123'
        )
        room = self.env['rental.room'].create(
            {'name': 'Telegram test', 'default_rent': 1000000}
        )
        self.inv = self.env['room.invoice'].create({'room_id': room.id})
        self.readings = self.env['meter.reading']

    def message(self, text, chat=123):
        return {'chat': {'id': chat}, 'from': {'id': chat}, 'text': text}

    def command(self, text):
        return self.readings.process_telegram_message(self.message(text))

    def test_pay_and_unpaid(self):
        self.assertEqual(
            self.command(f'/pay {self.inv.invoice_number} 100000')['status'],
            'success',
        )
        self.assertEqual(self.inv.paid_amount, 100000)
        self.assertEqual(self.inv.status, 'partially_paid')
        self.command(f'/paid {self.inv.invoice_number}')
        self.assertEqual(self.inv.status, 'paid')
        self.command(f'/unpaid {self.inv.invoice_number}')
        self.assertEqual(self.inv.paid_amount, 0)
        self.assertEqual(self.inv.status, 'pending')

    def test_overpayment_rolls_back(self):
        result = self.command(
            f'/pay {self.inv.invoice_number} {int(self.inv.total_amount + 1)}'
        )
        self.assertEqual(result['status'], 'error')
        self.assertEqual(self.inv.paid_amount, 0)
        self.assertEqual(self.inv.status, 'draft')

    def test_canceled_commands_rejected(self):
        self.inv.action_cancel()
        for text in (
            f'/pay {self.inv.invoice_number} 100000',
            f'/paid {self.inv.invoice_number}',
            f'/unpaid {self.inv.invoice_number}',
        ):
            self.assertEqual(self.command(text)['status'], 'error')
        self.assertEqual(self.inv.paid_amount, 0)
        self.assertEqual(self.inv.status, 'canceled')

    def test_sender_and_empty_allowlist(self):
        self.assertEqual(
            self.readings.process_telegram_message(
                self.message(
                    f'/pay {self.inv.invoice_number} 100000', chat=456
                )
            )['status'],
            'error',
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'room_rental_expense.telegram_allowed_chat_ids', ''
        )
        self.assertEqual(
            self.command(f'/pay {self.inv.invoice_number} 100000')['status'],
            'error',
        )
        self.assertEqual(self.inv.paid_amount, 0)

    def test_duplicate_update_and_distinct_updates(self):
        updates = self.env['room.telegram.update'].sudo()
        payload = {
            'update_id': 10,
            'message': self.message(f'/pay {self.inv.invoice_number} 100000'),
        }
        self.assertEqual(updates._process_update(payload)['status'], 'success')
        self.assertTrue(updates._process_update(payload)['duplicate'])
        self.assertEqual(self.inv.paid_amount, 100000)
        payload['update_id'] = 11
        updates._process_update(payload)
        self.assertEqual(self.inv.paid_amount, 200000)

    def test_receipts_not_publicly_accessible(self):
        updates = self.env['room.telegram.update'].with_user(
            self.env.ref('base.public_user')
        )
        with self.assertRaises(AccessError), self.cr.savepoint():
            updates.create({'bot_key': 'test', 'update_id': 1})
        with self.assertRaises(AccessError), self.cr.savepoint():
            updates.search([])


@tagged('post_install', '-at_install')
class TestTelegramWebhook(HttpCase):
    def setUp(self):
        super().setUp()
        self.icp = self.env['ir.config_parameter'].sudo()
        self.icp.set_param('room_rental_expense.telegram_bot_token', '')
        self.icp.set_param(
            'room_rental_expense.telegram_webhook_secret', 'test-secret'
        )
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '123'
        )
        room = self.env['rental.room'].create(
            {'name': 'HTTP test', 'default_rent': 1000000}
        )
        self.inv = self.env['room.invoice'].create(
            {'room_id': room.id, 'invoice_date': fields.Date.today()}
        )

    def post(self, payload, secret='test-secret'):
        return self.url_open(
            '/room_rental_expense/telegram/webhook',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-Telegram-Bot-Api-Secret-Token': secret,
            },
        )

    def payload(self, update_id=100):
        return {
            'update_id': update_id,
            'message': {
                'chat': {'id': 123},
                'text': f'/pay {self.inv.invoice_number} 100000',
            },
        }

    def test_authentication_required(self):
        self.assertEqual(
            self.post(self.payload(), secret='wrong').status_code, 403
        )
        self.icp.set_param('room_rental_expense.telegram_webhook_secret', '')
        self.assertEqual(self.post(self.payload()).status_code, 403)
        self.icp.set_param(
            'room_rental_expense.telegram_webhook_secret', 'test-secret'
        )
        self.icp.set_param('room_rental_expense.telegram_allowed_chat_ids', '')
        self.assertEqual(self.post(self.payload()).status_code, 403)
        self.inv.invalidate_recordset()
        self.assertEqual(self.inv.paid_amount, 0)

    def test_retry_and_edited_message(self):
        payload = self.payload()
        self.assertEqual(self.post(payload).json()['status'], 'success')
        self.assertTrue(self.post(payload).json()['duplicate'])
        edited = {'update_id': 101, 'edited_message': payload['message']}
        self.assertTrue(self.post(edited).json()['ignored'])
        self.inv.invalidate_recordset()
        self.assertEqual(self.inv.paid_amount, 100000)

    def test_invalid_update(self):
        payload = self.payload()
        payload.pop('update_id')
        self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.post(['invalid']).status_code, 400)
