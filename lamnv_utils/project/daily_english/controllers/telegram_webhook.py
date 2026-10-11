import secrets

from odoo import http
from odoo.http import request


class EnglishWebhook(http.Controller):

    @http.route(
        '/daily_english/telegram/webhook', type='http', auth='public',
        methods=['POST'], csrf=False,
    )
    def telegram_webhook(self):
        config = request.env['english.configuration']._get_config()
        supplied = request.httprequest.headers.get(
            'X-Telegram-Bot-Api-Secret-Token', ''
        )
        if (
            not config.webhook_secret or not config.telegram_token
            or not secrets.compare_digest(
                config.webhook_secret.encode(), supplied.encode()
            )
        ):
            return request.make_json_response({'ok': False}, status=403)
        if (request.httprequest.content_length or 0) > 16384:
            return request.make_json_response({'ok': False}, status=413)
        payload = request.httprequest.get_json(silent=True)
        if not isinstance(payload, dict):
            return request.make_json_response({'ok': False}, status=400)
        message = payload.get('message')
        if not isinstance(message, dict):
            return request.make_json_response({'ok': True, 'ignored': True})
        chat = message.get('chat')
        sender = message.get('from')
        text = message.get('text')
        if (
            type(payload.get('update_id')) is not int
            or payload['update_id'] < 0
            or not isinstance(chat, dict) or not isinstance(sender, dict)
            or chat.get('type') != 'private'
            or type(chat.get('id')) is not int or chat['id'] <= 0
            or type(sender.get('id')) is not int
            or sender['id'] != chat['id']
            or not isinstance(text, str) or not text.strip()
            or len(text) > 2000
        ):
            return request.make_json_response({'ok': True, 'ignored': True})
        request.env['english.update'].sudo()._process(payload)
        return request.make_json_response({'ok': True})
