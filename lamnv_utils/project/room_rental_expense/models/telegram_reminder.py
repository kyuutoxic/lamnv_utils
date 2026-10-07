import json
import logging
from datetime import timedelta
from urllib import error, request as urlrequest

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RoomTelegramReminder(models.Model):
    _name = 'room.telegram.reminder'
    _description = 'Nhắc Hạn Telegram'

    invoice_id = fields.Many2one(
        'room.invoice', required=True, ondelete='cascade'
    )
    chat_id = fields.Char(required=True)
    due_date = fields.Date(required=True)
    kind = fields.Selection(
        [('upcoming', 'Sắp đến hạn'), ('overdue', 'Quá hạn')], required=True
    )
    state = fields.Selection(
        [('pending', 'Chờ gửi'), ('sent', 'Đã gửi'), ('skipped', 'Bỏ qua')],
        default='pending',
    )
    _delivery_unique = models.Constraint(
        'unique(invoice_id, chat_id, due_date, kind)', 'Nhắc hạn đã tồn tại.'
    )

    @api.model
    def _run_reminders(self):
        icp = self.env['ir.config_parameter'].sudo()
        if (
            icp.get_param('room_rental_expense.telegram_reminders_enabled')
            != 'True'
        ):
            return
        token = icp.get_param('room_rental_expense.telegram_bot_token')
        chats = {
            item.strip()
            for item in icp.get_param(
                'room_rental_expense.telegram_allowed_chat_ids', ''
            ).split(',')
            if item.strip().lstrip('-').isdigit()
        }
        if not token or not chats:
            return
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
            ['room.telegram.reminders'],
        )
        try:
            days = max(
                0, int(icp.get_param('room_rental_expense.reminder_days', '3'))
            )
        except ValueError:
            days = 3
        today = fields.Date.context_today(self)
        invoices = self.env['room.invoice'].search(
            [
                ('status', 'not in', ['draft', 'paid', 'canceled']),
                ('remaining_amount', '>', 0),
                ('due_date', '!=', False),
                ('due_date', '<=', today + timedelta(days=days)),
            ]
        )
        for invoice in invoices:
            kind = 'overdue' if invoice.due_date < today else 'upcoming'
            for chat in chats:
                domain = [
                    ('invoice_id', '=', invoice.id),
                    ('chat_id', '=', chat),
                    ('due_date', '=', invoice.due_date),
                    ('kind', '=', kind),
                ]
                if not self.search_count(domain):
                    self.create(
                        dict(
                            invoice_id=invoice.id,
                            chat_id=chat,
                            due_date=invoice.due_date,
                            kind=kind,
                        )
                    )
        for delivery in self.search([('state', '=', 'pending')]):
            invoice = delivery.invoice_id
            current_kind = (
                'overdue' if delivery.due_date < today else 'upcoming'
            )
            if (
                delivery.chat_id not in chats
                or invoice.status in ('draft', 'paid', 'canceled')
                or invoice.remaining_amount <= 0
                or invoice.due_date != delivery.due_date
                or delivery.kind != current_kind
            ):
                delivery.state = 'skipped'
                continue
            label = 'Quá hạn' if delivery.kind == 'overdue' else 'Sắp đến hạn'
            remaining = invoice.room_id.format_vnd_amount(
                invoice.remaining_amount
            )
            text = (
                f'Nhắc thanh toán: {invoice.invoice_number}\n'
                f'Phòng: {invoice.room_id.name}\n'
                f'Hạn: {invoice.due_date}\n'
                f'Trạng thái: {label}\n'
                f'Còn lại: {remaining} VND'
            )
            if self._send_reminder(token, delivery.chat_id, text):
                delivery.state = 'sent'

    @api.model
    def _send_reminder(self, token, chat, text):
        req = urlrequest.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({'chat_id': chat, 'text': text}).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlrequest.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
            return isinstance(result, dict) and result.get('ok') is True
        except (error.URLError, TimeoutError, ValueError):
            _logger.warning('Telegram reminder failed; retry on next cron.')
            return False
