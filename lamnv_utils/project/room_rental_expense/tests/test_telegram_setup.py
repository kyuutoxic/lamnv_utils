import json
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib import error

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTelegramSetup(TransactionCase):
    def setUp(self):
        super().setUp()
        self.settings = self.env['res.config.settings'].create(
            {
                'telegram_bot_token': '123:test-only',
                'telegram_public_url': 'https://example.com',
                'telegram_allowed_chat_ids': '',
            }
        )
        self.icp = self.env['ir.config_parameter'].sudo()
        for key in (
            'telegram_bot_token',
            'telegram_webhook_secret',
            'telegram_allowed_chat_ids',
            'telegram_pairing_hash',
        ):
            self.icp.set_param(f'room_rental_expense.{key}', '')

    def api_response(self, result=True):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {
                'ok': True,
                'result': result,
            }
        ).encode()
        return response

    def connect(self):
        with patch('urllib.request.urlopen', return_value=self.api_response()):
            self.settings.action_connect_telegram()

    def pair(self, code=None, chat=123, kind='private'):
        command = code or self.settings.telegram_pairing_command
        return self.env['meter.reading'].process_telegram_message(
            {
                'text': command,
                'chat': {'id': chat, 'type': kind},
                'from': {'id': chat},
            }
        )

    def test_connect_registers_webhook_and_commands(self):
        with patch(
            'urllib.request.urlopen', return_value=self.api_response()
        ) as call:
            self.settings.action_connect_telegram()
        requests = [args.args[0] for args in call.call_args_list]
        payload = json.loads(requests[0].data)
        self.assertTrue(requests[0].full_url.endswith('/setWebhook'))
        self.assertEqual(
            payload['url'],
            'https://example.com/room_rental_expense/telegram/webhook',
        )
        self.assertRegex(payload['secret_token'], r'^[A-Za-z0-9_-]+$')
        self.assertEqual(payload['allowed_updates'], ['message'])
        self.assertFalse(payload['drop_pending_updates'])
        self.assertTrue(requests[1].full_url.endswith('/setMyCommands'))
        self.assertEqual(
            self.icp.get_param('room_rental_expense.telegram_bot_token'),
            '123:test-only',
        )
        self.assertTrue(self.settings.telegram_pairing_command)

    def test_invalid_url_and_secret_before_network(self):
        with patch('urllib.request.urlopen') as call:
            for url in (
                'http://example.com',
                'https://user@example.com',
                'https://example.com?token=abc',
            ):
                self.settings.telegram_public_url = url
                with self.assertRaises(UserError):
                    self.settings.action_connect_telegram()
            self.settings.telegram_public_url = 'https://example.com'
            self.settings.telegram_webhook_secret = '<invalid>'
            with self.assertRaises(UserError):
                self.settings.action_connect_telegram()
            call.assert_not_called()

    def test_pair_once_and_preserve_existing_chats(self):
        self.connect()
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '456'
        )
        command = self.settings.telegram_pairing_command
        self.assertEqual(self.pair()['status'], 'success')
        self.assertEqual(
            self.icp.get_param(
                'room_rental_expense.telegram_allowed_chat_ids'
            ),
            '456,123',
        )
        self.assertEqual(self.pair(command, chat=789)['status'], 'error')

    def test_pair_wrong_code_expired_and_group_rejected(self):
        self.connect()
        self.assertEqual(self.pair('/connect wrong')['status'], 'error')
        self.assertEqual(self.pair(kind='group')['status'], 'error')
        self.icp.set_param(
            'room_rental_expense.telegram_pairing_expiry',
            fields.Datetime.now() - timedelta(seconds=1),
        )
        self.assertEqual(self.pair()['status'], 'error')
        self.assertFalse(
            self.icp.get_param('room_rental_expense.telegram_allowed_chat_ids')
        )

    def test_regenerate_invalidates_previous_code(self):
        self.connect()
        previous = self.settings.telegram_pairing_command
        self.settings.action_generate_telegram_pairing()
        self.assertEqual(self.pair(previous)['status'], 'error')
        self.assertEqual(self.pair()['status'], 'success')

    def test_check_and_disconnect(self):
        self.connect()
        info = {
            'url': self.settings._telegram_webhook_url(),
            'pending_update_count': 2,
        }
        with patch(
            'urllib.request.urlopen', return_value=self.api_response(info)
        ):
            result = self.settings.action_check_telegram_connection()
        self.assertEqual(result['params']['type'], 'success')
        self.assertIn('2', self.settings.telegram_connection_info)
        with patch('urllib.request.urlopen', return_value=self.api_response()):
            self.settings.action_disconnect_telegram()
        self.assertFalse(
            self.icp.get_param('room_rental_expense.telegram_webhook_secret')
        )
        self.assertFalse(
            self.icp.get_param('room_rental_expense.telegram_pairing_hash')
        )

    def test_network_failure_does_not_leak_token(self):
        with patch(
            'urllib.request.urlopen',
            side_effect=error.URLError('123:test-only'),
        ):
            with self.assertRaises(UserError) as caught:
                self.settings.action_connect_telegram()
        self.assertNotIn('123:test-only', str(caught.exception))
        self.assertFalse(
            self.icp.get_param('room_rental_expense.telegram_webhook_secret')
        )

    def test_commands_failure_keeps_successful_connection(self):
        with patch(
            'urllib.request.urlopen',
            side_effect=[
                self.api_response(),
                error.URLError('offline'),
            ],
        ):
            result = self.settings.action_connect_telegram()
        self.assertEqual(result['params']['type'], 'warning')
        self.assertTrue(
            self.icp.get_param('room_rental_expense.telegram_webhook_secret')
        )

    def test_reconnect_preserves_paired_chat(self):
        self.connect()
        self.pair()
        self.assertFalse(self.settings.telegram_allowed_chat_ids)
        self.connect()
        self.assertEqual(self.settings.telegram_allowed_chat_ids, '123')

    def test_changed_bot_invalidates_pairing(self):
        self.connect()
        self.icp.set_param('room_rental_expense.telegram_bot_token', 'other')
        self.assertEqual(self.pair()['status'], 'error')
        with patch('urllib.request.urlopen') as call:
            with self.assertRaises(UserError):
                self.settings.action_disconnect_telegram()
            call.assert_not_called()

    def test_non_admin_cannot_connect(self):
        settings = self.settings.with_user(self.env.ref('base.public_user'))
        with patch('urllib.request.urlopen') as call:
            with self.assertRaises(UserError):
                settings.action_connect_telegram()
            call.assert_not_called()
