import json
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestTelegramOutbox(TransactionCase):
    def setUp(self):
        super().setUp()
        self.icp = self.env['ir.config_parameter'].sudo()
        self.icp.set_param(
            'room_rental_expense.telegram_bot_token', 'test-only'
        )
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '123'
        )
        self.updates = self.env['room.telegram.update'].sudo()
        self.outbox = self.env['room.telegram.outbox'].sudo()
        self.outbox.search([]).unlink()

    def enqueue(self, update_id=400, text='Test reply', markup=None):
        self.updates._process_update(
            {'update_id': update_id, 'message': {
                'chat': {'id': 123}, 'from': {'id': 123}, 'text': '/menu',
            }}
        )
        delivery = self.outbox.search(
            [('receipt_id.update_id', '=', update_id)]
        )
        delivery.write(
            {'parts': self.outbox._split_text(text), 'reply_markup': markup}
        )
        return delivery

    def ready(self, delivery):
        delivery.next_attempt = fields.Datetime.now() - timedelta(seconds=1)

    def response(self, body):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            body
        ).encode()
        return response

    def test_split_unicode_and_resume_without_resending(self):
        text = '😀' * 5000 + '\n' + 'a' * 5000
        parts = self.outbox._split_text(text)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(
            all(len(part.encode('utf-16-le')) // 2 <= 4000 for part in parts)
        )
        markup = {'keyboard': [['Hủy']]}
        delivery = self.enqueue(text='a' * 8001, markup=markup)
        with patch('urllib.request.urlopen', side_effect=[
            self.response({'ok': True}), URLError('test failure'),
        ]) as call:
            delivery._deliver()
        self.assertEqual(call.call_count, 2)
        self.assertEqual(delivery.next_part, 1)
        self.assertEqual(delivery.state, 'pending')
        self.ready(delivery)
        with patch('urllib.request.urlopen', return_value=self.response(
            {'ok': True}
        )) as call:
            delivery._deliver()
        self.assertEqual(call.call_count, 2)
        sent = json.loads(call.call_args.args[0].data)
        self.assertEqual(sent['reply_markup'], markup)
        self.assertEqual(delivery.state, 'sent')
        with patch('urllib.request.urlopen') as call:
            delivery._deliver()
        call.assert_not_called()

    def test_rate_limit_respects_retry_after(self):
        delivery = self.enqueue()
        before = fields.Datetime.now()
        body = {'ok': False, 'error_code': 429,
                'parameters': {'retry_after': 180}}
        with patch('urllib.request.urlopen', return_value=self.response(body)):
            delivery._deliver()
        self.assertEqual(delivery.state, 'pending')
        self.assertGreaterEqual(
            delivery.next_attempt, before + timedelta(seconds=180)
        )
        with patch('urllib.request.urlopen') as call:
            delivery._deliver()
        call.assert_not_called()

    def test_permanent_error_and_retry_limit(self):
        delivery = self.enqueue()
        with patch('urllib.request.urlopen', return_value=self.response(
            {'ok': False, 'error_code': 403}
        )):
            delivery._deliver()
        self.assertEqual(delivery.state, 'failed')
        delivery = self.enqueue(update_id=401)
        for attempt in range(5):
            self.ready(delivery)
            with patch('urllib.request.urlopen', side_effect=URLError('test')):
                delivery._deliver()
        self.assertEqual(delivery.attempts, 5)
        self.assertEqual(delivery.state, 'failed')

    def test_chat_revoked_or_bot_changed(self):
        delivery = self.enqueue()
        self.icp.set_param('room_rental_expense.telegram_allowed_chat_ids', '')
        with patch('urllib.request.urlopen') as call:
            delivery._deliver()
        call.assert_not_called()
        self.assertEqual(delivery.state, 'skipped')
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '123'
        )
        delivery = self.enqueue(update_id=401)
        self.icp.set_param('room_rental_expense.telegram_bot_token', 'new-bot')
        with patch('urllib.request.urlopen') as call:
            delivery._deliver()
        call.assert_not_called()
        self.assertEqual(delivery.state, 'skipped')

    def test_duplicate_update_and_rollback(self):
        delivery = self.enqueue()
        self.enqueue()
        self.assertEqual(self.outbox.search_count([]), 1)
        self.assertEqual(delivery.state, 'pending')
        with self.assertRaises(ValueError):
            with self.env.cr.savepoint():
                self.enqueue(update_id=401)
                raise ValueError('rollback')
        self.assertFalse(self.updates.search([('update_id', '=', 401)]))
        self.assertEqual(self.outbox.search_count([]), 1)

    def test_cron_preserves_chat_order(self):
        first = self.enqueue(markup={'keyboard': [['Old menu']]})
        second = self.enqueue(update_id=401)
        first.next_attempt = fields.Datetime.now() + timedelta(minutes=5)
        with patch('urllib.request.urlopen') as call:
            second._deliver()
        call.assert_not_called()
        self.ready(first)
        self.ready(second)
        cron_user = new_test_user(self.env, login='outbox_cron_user')
        with patch('urllib.request.urlopen', return_value=self.response(
            {'ok': True}
        )) as call:
            self.outbox.with_user(cron_user)._cron_retry()
        self.assertEqual(call.call_count, 2)
        first_sent = json.loads(call.call_args_list[0].args[0].data)
        self.assertNotIn('reply_markup', first_sent)
        self.assertEqual(first.state, 'sent')
        self.assertEqual(second.state, 'sent')

    def test_http_error_and_invalid_json(self):
        delivery = self.enqueue()
        with patch('urllib.request.urlopen', side_effect=HTTPError(
            'https://example.invalid', 502, 'test', {}, None
        )):
            delivery._deliver()
        self.assertEqual(delivery.state, 'pending')
        self.assertEqual(delivery.last_error, 'API 502')
        self.ready(delivery)
        response = self.response({'ok': True})
        response.__enter__.return_value.read.return_value = b'invalid-json'
        with patch('urllib.request.urlopen', return_value=response):
            delivery._deliver()
        self.assertEqual(delivery.state, 'pending')
        self.assertEqual(delivery.last_error, 'Network/JSON')

    def test_manual_retry_is_admin_only_and_keeps_progress(self):
        delivery = self.enqueue(text='a' * 8001)
        delivery.write({'state': 'failed', 'next_part': 1, 'attempts': 5})
        user = new_test_user(self.env, login='outbox_user')
        with self.assertRaises(AccessError):
            delivery.with_user(user).action_retry()
        delivery.action_retry()
        self.assertEqual(delivery.state, 'pending')
        self.assertEqual(delivery.next_part, 1)
        self.assertEqual(delivery.attempts, 0)
        with patch('urllib.request.urlopen', return_value=self.response(
            {'ok': True}
        )) as call:
            self.outbox._cron_retry()
        self.assertEqual(call.call_count, 2)
        self.assertEqual(delivery.state, 'sent')
