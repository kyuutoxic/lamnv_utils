import hashlib
import json
import logging
from datetime import timedelta
from urllib import error, request as urlrequest

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class RoomTelegramOutbox(models.Model):
    _name = 'room.telegram.outbox'
    _description = 'Hàng Đợi Phản Hồi Telegram'
    _order = 'id'

    receipt_id = fields.Many2one(
        'room.telegram.update', required=True, ondelete='cascade'
    )
    bot_key = fields.Char(required=True)
    chat_id = fields.Char(required=True)
    parts = fields.Json(required=True)
    reply_markup = fields.Json()
    next_part = fields.Integer(default=0)
    attempts = fields.Integer(default=0)
    next_attempt = fields.Datetime(default=fields.Datetime.now)
    state = fields.Selection(
        [('pending', 'Chờ gửi'), ('sent', 'Đã gửi'),
         ('failed', 'Gửi thất bại'), ('skipped', 'Bỏ qua')],
        default='pending', required=True,
    )
    last_error = fields.Char()
    _receipt_unique = models.Constraint(
        'unique(receipt_id)', 'Phản hồi đã nằm trong hàng đợi.'
    )

    @api.model
    def _split_text(self, text):
        parts = []
        while text:
            # Count UTF-16 units conservatively, including emoji.
            size = 0
            end = 0
            for char in text:
                size += 2 if ord(char) > 0xFFFF else 1
                if size > 4000:
                    break
                end += 1
            if end < len(text):
                newline = text.rfind('\n', 0, end)
                if newline >= end // 2:
                    end = newline + 1
            parts.append(text[:end])
            text = text[end:]
        return parts

    @api.model
    def _enqueue(self, receipt, message, result):
        token = self.env['ir.config_parameter'].sudo().get_param(
            'room_rental_expense.telegram_bot_token', ''
        )
        chat = (message.get('chat') or {}).get('id')
        text = result.get('message')
        if not token or type(chat) is not int or not text:
            return self.browse()
        delivery = self.create(
            {
                'receipt_id': receipt.id,
                'bot_key': receipt.bot_key,
                'chat_id': str(chat),
                'parts': self._split_text(text),
                'reply_markup': result.get('reply_markup'),
            }
        )
        dbname = self.env.cr.dbname
        delivery_id = delivery.id

        @self.env.cr.postcommit.add
        def send_after_commit():
            try:
                with Registry(dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    env['room.telegram.outbox'].browse(delivery_id)._deliver()
                    cr.commit()
            except Exception:
                # Queue remains pending if the delivery transaction fails.
                _logger.warning('Telegram reply delivery deferred to cron.')

        return delivery

    def _deliver(self):
        self.ensure_one()
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
            [f'room.telegram.outbox:{self.bot_key}:{self.chat_id}'],
        )
        self.env.cr.execute(
            'SELECT id FROM room_telegram_outbox '
            'WHERE id = %s FOR UPDATE', [self.id],
        )
        self.invalidate_recordset()
        if self.state != 'pending':
            return
        if self.search_count(
            [('bot_key', '=', self.bot_key), ('chat_id', '=', self.chat_id),
             ('state', '=', 'pending'), ('id', '<', self.id)]
        ):
            return
        now = fields.Datetime.now()
        if self.next_attempt and self.next_attempt > now:
            return
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('room_rental_expense.telegram_bot_token', '')
        allowed = {
            value.strip() for value in icp.get_param(
                'room_rental_expense.telegram_allowed_chat_ids', ''
            ).split(',')
        }
        if (
            not token
            or hashlib.sha256(token.encode()).hexdigest() != self.bot_key
            or self.chat_id not in allowed
        ):
            self.write({'state': 'skipped', 'last_error': 'Bot/chat changed'})
            return
        while self.next_part < len(self.parts):
            data = {
                'chat_id': self.chat_id, 'text': self.parts[self.next_part]
            }
            newer = self.search_count(
                [('bot_key', '=', self.bot_key),
                 ('chat_id', '=', self.chat_id), ('id', '>', self.id)]
            )
            if (
                self.reply_markup and not newer
                and self.next_part == len(self.parts) - 1
            ):
                data['reply_markup'] = self.reply_markup
            result = self._send(token, data)
            if result.get('ok') is True:
                self.write(
                    {'next_part': self.next_part + 1, 'attempts': 0,
                     'last_error': False}
                )
                continue
            code = result.get('error_code')
            attempts = self.attempts + 1
            retry = code in (None, 429) or (
                isinstance(code, int) and code >= 500
            )
            parameters = result.get('parameters') or {}
            delay = parameters.get('retry_after')
            if type(delay) is not int or delay <= 0:
                delay = min(3600, 60 * 2 ** (attempts - 1))
            self.write(
                {
                    'attempts': attempts,
                    'state': (
                        'pending' if retry and attempts < 5 else 'failed'
                    ),
                    'next_attempt': now + timedelta(seconds=delay),
                    'last_error': f'API {code}' if code else 'Network/JSON',
                }
            )
            return
        self.state = 'sent'

    @api.model
    def _send(self, token, data):
        req = urlrequest.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST',
        )
        try:
            with urlrequest.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
        except error.HTTPError as exc:
            try:
                result = json.loads(exc.read())
            except (ValueError, TypeError):
                result = {'error_code': exc.code}
            if not isinstance(result, dict):
                result = {'error_code': exc.code}
            result.setdefault('error_code', exc.code)
        except (error.URLError, TimeoutError, ValueError, TypeError):
            return {}
        return result if isinstance(result, dict) else {}

    @api.model
    def _cron_retry(self):
        deliveries = self.sudo().search(
            [('state', '=', 'pending'),
             ('next_attempt', '<=', fields.Datetime.now())], limit=20,
        )
        for delivery in deliveries:
            delivery._deliver()

    def action_retry(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Chỉ quản trị viên được gửi lại phản hồi.')
        self.sudo().filtered(lambda item: item.state == 'failed').write(
            {'state': 'pending', 'attempts': 0,
             'next_attempt': fields.Datetime.now(), 'last_error': False}
        )
        return True
