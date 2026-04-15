import json
import logging
from urllib import error, request as urlrequest

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class RoomRentalTelegramWebhook(http.Controller):

    @http.route(
        '/room_rental_expense/telegram/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def telegram_webhook(self, **kwargs):
        payload = request.httprequest.get_json(silent=True) or {}
        env = request.env
        icp = env['ir.config_parameter'].sudo()
        configured_secret = icp.get_param(
            'room_rental_expense.telegram_webhook_secret'
        )
        provided_secret = (
            request.httprequest.headers.get('X-Telegram-Bot-Api-Secret-Token')
            or kwargs.get('secret')
        )
        if configured_secret and provided_secret != configured_secret:
            _logger.warning('Rejected Telegram webhook with invalid secret.')
            return request.make_json_response(
                {'ok': False, 'error': 'invalid_secret'},
                status=403,
            )

        message = payload.get('message') or payload.get('edited_message') or {}
        if not message:
            return request.make_json_response({'ok': True, 'ignored': True})

        result = env['meter.reading'].sudo().process_telegram_message(message)
        self._send_telegram_reply(
            token=icp.get_param('room_rental_expense.telegram_bot_token'),
            chat_id=message.get('chat', {}).get('id'),
            text=result.get('message'),
        )
        return request.make_json_response(result, status=200)

    def _send_telegram_reply(self, token, chat_id, text):
        if not token or not chat_id or not text:
            return
        endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = json.dumps({
            'chat_id': chat_id,
            'text': text,
        }).encode('utf-8')
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlrequest.urlopen(req, timeout=10):
                return
        except error.URLError:
            _logger.exception('Failed to send Telegram reply.')
