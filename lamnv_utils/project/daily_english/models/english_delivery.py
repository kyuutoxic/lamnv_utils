import hashlib
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


KEYBOARD = {
    'keyboard': [
        ['📖 Bài học', '🧩 Giải thích'],
        ['💡 Gợi ý', '⏭ Bỏ qua'],
        ['✅ Đáp án', '📊 Tiến độ'],
        ['🛑 Dừng buổi'],
        ['⏸ Tạm nghỉ', '▶️ Học tiếp'],
    ],
    'resize_keyboard': True,
}


def split_message(text, limit=3800):
    parts = []
    chunk = []
    size = 0
    for char in text:
        units = len(char.encode('utf-16-le')) // 2
        if size + units > limit:
            parts.append(''.join(chunk))
            chunk, size = [], 0
        chunk.append(char)
        size += units
    if chunk:
        parts.append(''.join(chunk))
    return parts


class EnglishDelivery(models.Model):
    _name = 'english.delivery'
    _description = 'English Telegram Outbox'
    _order = 'id'
    _rec_name = 'learner_id'

    learner_id = fields.Many2one(
        'english.learner', required=True, ondelete='cascade', index=True,
    )
    chat_id = fields.Char(required=True)
    bot_hash = fields.Char(required=True)
    text = fields.Text(required=True)
    keyboard = fields.Boolean()
    automatic = fields.Boolean()
    session_id = fields.Many2one('english.session', ondelete='set null')
    state = fields.Selection([
        ('pending', 'Chờ gửi'), ('sending', 'Đang gửi'), ('sent', 'Đã gửi'),
        ('failed', 'Lỗi'), ('skipped', 'Bỏ qua'),
    ], default='pending', required=True, index=True)
    attempts = fields.Integer(default=0)
    next_part = fields.Integer(default=0)
    next_run = fields.Datetime(default=fields.Datetime.now, index=True)
    error_code = fields.Char(readonly=True)

    @api.model
    def _enqueue(self, learner, text, keyboard=False, automatic=False,
                 session=None):
        config = self.env['english.configuration']._get_config()
        if not learner.chat_id:
            return self.browse()
        delivery = self.create({
            'learner_id': learner.id, 'chat_id': learner.chat_id,
            'bot_hash': hashlib.sha256(
                (config.telegram_token or '').encode()
            ).hexdigest(),
            'text': text, 'keyboard': keyboard, 'automatic': automatic,
            'session_id': session.id if session else False,
        })

        self.env.ref('daily_english.cron_english_delivery')._trigger()
        return delivery

    def _allowed(self, config):
        learner = self.learner_id
        current_hash = hashlib.sha256(
            (config.telegram_token or '').encode()
        ).hexdigest()
        return (
            learner.active and learner.chat_id == self.chat_id
            and self.bot_hash == current_hash
            and learner.bot_hash == current_hash
            and not (self.automatic and learner.paused)
            and self.session_id.state != 'stopped'
        )

    @api.model
    def _cron_send(self):
        config = self.env['english.configuration']._get_config()
        for stale in self.sudo().search([
            ('state', '=', 'sending'),
            ('next_run', '<=', fields.Datetime.now()),
        ], limit=20):
            stale.learner_id._lock()
            stale.invalidate_recordset()
            if stale.state == 'sending':
                stale.state = 'pending'
        deliveries = self.sudo().search([
            ('state', '=', 'pending'),
            ('next_run', '<=', fields.Datetime.now()),
        ], limit=20)
        for delivery in deliveries:
            delivery.learner_id._lock()
            self.env.cr.execute(
                'SELECT id FROM english_delivery WHERE id = %s FOR UPDATE',
                [delivery.id],
            )
            delivery.invalidate_recordset()
            if delivery.state != 'pending':
                continue
            older = self.sudo().search_count([
                ('learner_id', '=', delivery.learner_id.id),
                ('state', 'in', ['pending', 'sending']),
                ('id', '<', delivery.id),
            ])
            if older:
                continue
            if not delivery._allowed(config):
                delivery.state = 'skipped'
                continue
            parts = split_message(delivery.text)
            try:
                for index in range(delivery.next_part, len(parts)):
                    if not delivery._allowed(config):
                        delivery.state = 'skipped'
                        break
                    payload = {
                        'chat_id': delivery.chat_id, 'text': parts[index],
                    }
                    if delivery.keyboard and index == len(parts) - 1:
                        payload['reply_markup'] = KEYBOARD
                    delivery.write({
                        'state': 'sending',
                        'next_run': fields.Datetime.now()
                        + timedelta(minutes=2),
                    })
                    self.env['ir.cron']._commit_progress(remaining=1)
                    config._telegram('sendMessage', payload)
                    self.env['ir.cron']._commit_progress(remaining=1)
                    self.env.invalidate_all()
                    delivery.learner_id._lock()
                    if delivery.state != 'sending':
                        break
                    delivery.write({'next_part': index + 1, 'attempts': 0})
                if delivery.state == 'sending':
                    delivery.write({'state': 'sent', 'error_code': False})
            except UserError:
                self.env['ir.cron']._commit_progress(remaining=1)
                self.env.invalidate_all()
                delivery.learner_id._lock()
                if delivery.state != 'sending':
                    continue
                attempts = delivery.attempts + 1
                delivery.write({
                    'attempts': attempts,
                    'state': 'failed' if attempts >= 5 else 'pending',
                    'error_code': 'telegram_unavailable',
                    'next_run': fields.Datetime.now()
                    + timedelta(seconds=min(60 * 2 ** attempts, 3600)),
                })

        self.env['english.job']._wake_due_workers()
        progressed = any(d.state != 'pending' for d in deliveries)
        if progressed and len(deliveries) == 20 and self.sudo().search_count([
            ('state', '=', 'pending'),
            ('next_run', '<=', fields.Datetime.now()),
        ], limit=1):
            self.env.ref('daily_english.cron_english_delivery')._trigger()

        self.env['ir.cron']._commit_progress(1, remaining=0)

    def action_retry(self):
        self.check_access('write')
        for delivery in self.filtered(lambda item: item.state == 'failed'):
            delivery.write({
                'state': 'pending', 'attempts': 0,
                'next_run': fields.Datetime.now(),
            })
        self.env.ref('daily_english.cron_english_delivery')._trigger()
