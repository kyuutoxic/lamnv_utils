import hashlib
import json
from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from ..models.english_configuration import gemini_api_error


@tagged('post_install', '-at_install')
class TestEnglishWebhook(HttpCase):

    def setUp(self):
        super().setUp()
        self.config = self.env.ref('daily_english.configuration_default')
        self.config.write({
            'telegram_token': 'test-only-token',
            'webhook_secret': 'test-only-secret-123456',
        })
        self.learner = self.env['english.learner'].create({
            'curriculum_enabled': False,
            'name': 'HTTP learner', 'chat_id': '123',
            'bot_hash': hashlib.sha256(b'test-only-token').hexdigest(),
        })

    def post(self, payload, secret='test-only-secret-123456'):
        return self.url_open(
            '/daily_english/telegram/webhook',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-Telegram-Bot-Api-Secret-Token': secret,
            },
        )

    def payload(self, text='/lesson'):
        return {
            'update_id': 500,
            'message': {
                'chat': {'id': 123, 'type': 'private'},
                'from': {'id': 123}, 'text': text,
            },
        }

    def test_secret_required(self):
        response = self.post(self.payload(), secret='wrong')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.env['english.progress'].search([]))

    def test_webhook_replay_no_duplicate_lesson(self):
        for unused in range(2):
            response = self.post(self.payload())
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.env['english.progress'].search_count([]), 1)
        self.assertEqual(self.env['english.delivery'].search_count([]), 1)

    def test_invalid_sender_group_and_edited_ignored(self):
        payload = self.payload()
        payload['message']['from']['id'] = 456
        self.assertTrue(self.post(payload).json()['ignored'])
        payload['message']['from']['id'] = 123
        payload['message']['chat']['type'] = 'group'
        self.assertTrue(self.post(payload).json()['ignored'])
        self.assertTrue(self.post({
            'update_id': 501, 'edited_message': self.payload()['message'],
        }).json()['ignored'])
        self.assertFalse(self.env['english.progress'].search([]))

    def test_invalid_body_and_large_payload(self):
        self.assertEqual(self.post([]).status_code, 400)
        self.assertEqual(self.post(self.payload('x' * 20000)).status_code, 413)

    def test_gemini_button_error_serializes_as_standard_user_error(self):
        self.config.write({
            'gemini_key': 'test-only-key', 'gemini_model': 'gemini-2.5-flash',
        })
        self.authenticate('admin', 'admin')
        payload = {
            'jsonrpc': '2.0', 'id': 1, 'method': 'call',
            'params': {
                'model': 'english.configuration',
                'method': 'action_test_gemini',
                'args': [[self.config.id]], 'kwargs': {},
            },
        }
        with patch.object(
            type(self.config), '_post_json', side_effect=gemini_api_error(404)
        ):
            response = self.url_open(
                '/web/dataset/call_button', data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
            )
        body = response.json()
        self.assertEqual(body['error']['data']['name'],
                         'odoo.exceptions.UserError')
        self.assertIn('404', body['error']['data']['message'])
        self.assertNotIn('test-only-key', body['error']['data']['message'])
