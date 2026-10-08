import logging

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
        provided_secret = request.httprequest.headers.get(
            'X-Telegram-Bot-Api-Secret-Token'
        ) or kwargs.get('secret')
        if not configured_secret or provided_secret != configured_secret:
            _logger.warning('Rejected Telegram webhook with invalid secret.')
            return request.make_json_response(
                {'ok': False, 'error': 'invalid_secret'},
                status=403,
            )

        if not isinstance(payload, dict):
            return request.make_json_response(
                {'ok': False, 'error': 'invalid_update'}, status=400
            )
        message = payload.get('message') or {}
        text = message.get('text', '') if isinstance(message, dict) else ''
        pairing = isinstance(text, str) and text.lower().split()[:1] == [
            '/connect'
        ]
        if (
            not pairing
            and not icp.get_param(
                'room_rental_expense.telegram_allowed_chat_ids', ''
            ).strip()
        ):
            return request.make_json_response(
                {'ok': False, 'error': 'allowed_chats_not_configured'},
                status=403,
            )
        if not message:
            return request.make_json_response({'ok': True, 'ignored': True})

        update_id = payload.get('update_id')
        if (
            not isinstance(message, dict)
            or type(update_id) is not int
            or update_id < 0
        ):
            return request.make_json_response(
                {'ok': False, 'error': 'invalid_update'}, status=400
            )
        result = env['room.telegram.update'].sudo()._process_update(payload)
        return request.make_json_response(result, status=200)
